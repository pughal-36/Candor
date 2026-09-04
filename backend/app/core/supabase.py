import logging
import time
from typing import Any
import postgrest._sync.request_builder as rb
from supabase import create_client, Client
from app.core.config import settings

logger = logging.getLogger(__name__)


# Patch postgrest request builders so ALL .execute() calls across the entire codebase
# automatically retry on transient HTTP/2 / PostgREST network drops / disconnects.
_CLASSES_TO_PATCH = [
    rb.SyncFilterRequestBuilder,
    rb.SyncSelectRequestBuilder,
    rb.SyncQueryRequestBuilder,
    rb.SyncSingleRequestBuilder,
    rb.SyncMaybeSingleRequestBuilder,
    rb.SyncRPCFilterRequestBuilder,
    rb.SyncExplainRequestBuilder,
]

for _cls in _CLASSES_TO_PATCH:
    if hasattr(_cls, "execute"):
        _orig_exec = getattr(_cls, "execute")

        def _make_retry_wrapper(orig_fn):
            def wrapper(self, *args, **kwargs):
                last_exc = None
                for attempt in range(3):
                    try:
                        return orig_fn(self, *args, **kwargs)
                    except Exception as exc:
                        last_exc = exc
                        logger.warning(
                            "PostgREST query attempt %d/3 failed: %s. Retrying...",
                            attempt + 1,
                            exc,
                        )
                        time.sleep(0.15 * (2 ** attempt))
                raise last_exc

            return wrapper

        setattr(_cls, "execute", _make_retry_wrapper(_orig_exec))


def _make_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


supabase: Client = _make_client()


def safe_execute(query_builder: Any, retries: int = 3) -> Any:
    """
    Execute a Supabase query builder with automatic retries for transient HTTP/2 / PostgREST disconnects.
    """
    last_exc = None
    for attempt in range(retries):
        try:
            return query_builder.execute()
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Supabase query failed on attempt %d/%d: %s. Retrying...",
                attempt + 1,
                retries,
                exc,
            )
            time.sleep(0.1 * (2 ** attempt))
    raise last_exc


def ensure_storage_bucket(bucket_name: str = "statements") -> None:
    """Ensure the specified storage bucket exists in Supabase Storage."""
    try:
        supabase.storage.get_bucket(bucket_name)
    except Exception:
        try:
            supabase.storage.create_bucket(bucket_name, options={"public": True})
            logger.info("Created Supabase storage bucket: %s", bucket_name)
        except Exception as exc:
            logger.warning("Storage bucket check/create warning for '%s': %s", bucket_name, exc)


def upload_file_to_storage(
    bucket_name: str,
    file_path: str,
    file_bytes: bytes,
    content_type: str = "application/pdf"
) -> str:
    """Upload a file to Supabase Storage and return its storage path."""
    ensure_storage_bucket(bucket_name)
    res = supabase.storage.from_(bucket_name).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    full_path = getattr(res, "full_path", getattr(res, "fullPath", f"{bucket_name}/{file_path}"))
    logger.info("[UPLOAD TRACE] Uploaded file to Supabase Storage: %s", full_path)
    return str(full_path)

