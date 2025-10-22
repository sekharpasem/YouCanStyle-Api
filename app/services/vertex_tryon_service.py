from typing import Optional
import io
import os
import json
import base64
import tempfile
import inspect

from app.core.config import settings

# OAuth scopes required for Vertex AI
SCOPES = [
    "https://www.googleapis.com/auth/cloud-platform",
]

# Optional: Vertex AI imports guarded to avoid import errors if not installed
try:
    from google.cloud import aiplatform  # may still be needed by underlying SDK
    import vertexai
    try:
        # Preferred modern namespace
        from vertexai.vision_models import ImageGenerationModel, Image as VertexImage  # type: ignore
        print("[TryOn] Using vertexai.vision_models namespace")
    except Exception:
        # Fallback to preview namespace on older SDKs
        from vertexai.preview.vision_models import ImageGenerationModel, Image as VertexImage  # type: ignore
        print("[TryOn] Using vertexai.preview.vision_models namespace")
    VERTEX_AVAILABLE = True
except Exception as e:
    print(f"[TryOn] Vertex AI SDK not available: {e}")
    VERTEX_AVAILABLE = False

# GenAI (official Virtual Try-On API) imports
try:
    from google import genai
    GENAI_AVAILABLE = True
    try:
        from google.genai.types import RecontextImageSource as RecontextImageSource  # type: ignore
        from google.genai.types import ProductImage as ProductImage  # type: ignore
        from google.genai.types import Image as GenImage  # type: ignore
        GENAI_TYPED_AVAILABLE = True
    except Exception as e:
        GENAI_TYPED_AVAILABLE = False
        GenImage = None  # type: ignore
        print(f"[TryOn] google-genai typed helpers unavailable: {e}")
except Exception as e:
    print(f"[TryOn] google-genai SDK not available: {e}")
    GENAI_AVAILABLE = False


async def generate_tryon_image(person_bytes: bytes, garment_bytes: bytes) -> Optional[bytes]:
    """
    Attempt to generate a try-on image using Vertex AI. Returns PNG bytes on success, or None to fallback.
    Note: Proper implementation requires a supported Vertex AI image model and tuning. This function provides
    a guarded scaffold and may return None if not configured.
    """
    if not VERTEX_AVAILABLE:
        print("[TryOn] Skipping Vertex: SDK not available")
        return None

    project = getattr(settings, "GCP_PROJECT_ID", None)
    location = getattr(settings, "GCP_LOCATION", "us-central1")
    model_name = getattr(settings, "VERTEX_IMAGE_MODEL", "imagen-3.0-generate")

    if not project:
        print("[TryOn] Skipping Vertex: GCP_PROJECT_ID not set")
        return None

    try:
        # Initialize Vertex with explicit credentials if available
        creds = None
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_path and os.path.isfile(cred_path):
            try:
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
                print("[TryOn] Using GOOGLE_APPLICATION_CREDENTIALS for Vertex")
            except Exception as e:
                print(f"[TryOn] Failed to load GOOGLE_APPLICATION_CREDENTIALS: {e}")
                creds = None
        elif settings.GOOGLE_SA_JSON_BASE64:
            try:
                from google.oauth2 import service_account
                info = json.loads(base64.b64decode(settings.GOOGLE_SA_JSON_BASE64))
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
                print("[TryOn] Using GOOGLE_SA_JSON_BASE64 for Vertex")
            except Exception as e:
                print(f"[TryOn] Failed to load GOOGLE_SA_JSON_BASE64: {e}")
                creds = None
        elif settings.GOOGLE_SA_JSON_PATH:
            try:
                from google.oauth2 import service_account
                with open(settings.GOOGLE_SA_JSON_PATH, "r", encoding="utf-8") as f:
                    info = json.load(f)
                creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
                print("[TryOn] Using GOOGLE_SA_JSON_PATH for Vertex")
            except Exception as e:
                print(f"[TryOn] Failed to load GOOGLE_SA_JSON_PATH: {e}")
                creds = None

        try:
            # Set quota project to ensure requests are billed to the target project
            if creds is not None and hasattr(creds, 'with_quota_project'):
                creds = creds.with_quota_project(project)
            if creds is not None:
                vertexai.init(project=project, location=location, credentials=creds)
            else:
                vertexai.init(project=project, location=location)
        except Exception as e:
            print(f"[TryOn] vertexai.init failed, trying aiplatform.init: {e}")
            aiplatform.init(project=project, location=location, credentials=creds)
        model = ImageGenerationModel.from_pretrained(model_name)

        # Load images (robust to SDK differences)
        def _load_vertex_image_from_bytes(label: str, data: bytes):
            try:
                if hasattr(VertexImage, "from_bytes"):
                    print(f"[TryOn] Loading {label} via VertexImage.from_bytes")
                    return VertexImage.from_bytes(data)  # type: ignore[attr-defined]
                if hasattr(VertexImage, "load_from_bytes"):
                    print(f"[TryOn] Loading {label} via VertexImage.load_from_bytes")
                    return VertexImage.load_from_bytes(data)  # type: ignore[attr-defined]
            except Exception as e:
                print(f"[TryOn] Direct bytes load failed for {label}: {e}")

            # Fallback: write to a temp file and load_from_file
            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name
                if hasattr(VertexImage, "load_from_file"):
                    print(f"[TryOn] Loading {label} via VertexImage.load_from_file")
                    return VertexImage.load_from_file(tmp_path)  # type: ignore[attr-defined]
            except Exception as e:
                print(f"[TryOn] Fallback file load failed for {label}: {e}")
            return None

        person_img = _load_vertex_image_from_bytes("person", person_bytes)

        # IMPORTANT: This is a placeholder prompt. Proper virtual try-on requires advanced workflows.
        prompt = (
            "Overlay and fit the garment image naturally on the person image, preserving human anatomy and proportions. "
            "Generate a realistic try-on preview."
        )

        # Some SDK versions do not accept 'image' in generate_images().
        accepts_image = False
        try:
            sig = inspect.signature(model.generate_images)
            accepts_image = 'image' in sig.parameters
        except Exception:
            accepts_image = False

        if person_img is not None and accepts_image:
            print("[TryOn] generate_images supports 'image' - sending person image")
            try:
                images = model.generate_images(
                    prompt=prompt,
                    number_of_images=1,
                    image=person_img,
                    negative_prompt="distorted body, artifacts, deformed hands",
                )
            except TypeError as e:
                # Some SDK builds report 'unexpected keyword argument \"image\"' at runtime
                print(f"[TryOn] 'image' kwarg rejected by SDK ({e}); retrying prompt-only")
                images = model.generate_images(
                    prompt=prompt,
                    number_of_images=1,
                    negative_prompt="distorted body, artifacts, deformed hands",
                )
        else:
            if person_img is not None and not accepts_image:
                print("[TryOn] generate_images does NOT accept 'image' - switching to prompt-only")
            else:
                print("[TryOn] Proceeding without image conditioning (prompt-only)")
            images = model.generate_images(
                prompt=prompt,
                number_of_images=1,
                negative_prompt="distorted body, artifacts, deformed hands",
            )

        if not images:
            print("[TryOn] Vertex returned no images")
            return None

        # The SDK object may provide PIL image bytes via ._image_bytes or .image
        try:
            # Newer SDKs may have ._image_bytes
            data = images[0]._image_bytes  # type: ignore[attr-defined]
        except Exception:
            # Fallback: get bytes via as_bytes() if available
            try:
                data = images[0].as_bytes()
            except Exception as e:
                print(f"[TryOn] Unable to extract bytes from Vertex image: {e}")
                return None

        return data
    except Exception as e:
        # Swallow errors to allow fallback, but log why
        print(f"[TryOn] Vertex generation error: {e}")
        return None


async def generate_vertex_vto(person_bytes: bytes, garment_bytes: bytes) -> bytes:
    """
    Call the official Vertex Virtual Try-On API via REST.
    Returns raw PNG/JPEG bytes. Raises Exception on any failure. No fallbacks.
    """
    import base64 as _b64
    import httpx
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as AuthRequest

    project = getattr(settings, "GCP_PROJECT_ID", None)
    region = getattr(settings, "GCP_LOCATION", None) or "us-central1"
    model_name = getattr(settings, "VERTEX_IMAGE_MODEL", "virtual-try-on-preview-08-04")

    if not project:
        raise RuntimeError("GCP_PROJECT_ID not set")
    # Map 'global' to a concrete region for REST
    if str(region).lower() == "global":
        region = "us-central1"

    # Build URL
    url = (
        f"https://{region}-aiplatform.googleapis.com/v1/projects/"
        f"{project}/locations/{region}/publishers/google/models/{model_name}:predict"
    )

    # Load credentials (same scopes as before)
    SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
    creds = None
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    try:
        if cred_path and os.path.isfile(cred_path):
            creds = service_account.Credentials.from_service_account_file(cred_path, scopes=SCOPES)
        elif getattr(settings, "GOOGLE_SA_JSON_BASE64", None):
            info = json.loads(base64.b64decode(settings.GOOGLE_SA_JSON_BASE64))
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        elif getattr(settings, "GOOGLE_SA_JSON_PATH", None):
            with open(settings.GOOGLE_SA_JSON_PATH, "r", encoding="utf-8") as f:
                info = json.load(f)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            raise RuntimeError("No service account credentials configured")
    except Exception as e:
        raise RuntimeError(f"Failed to load credentials: {e}")

    # Ensure token
    creds = creds.with_quota_project(project) if hasattr(creds, "with_quota_project") else creds
    try:
        creds.refresh(AuthRequest())
    except Exception as e:
        raise RuntimeError(f"Auth token refresh failed: {e}")

    # Prepare request body
    body = {
        "instances": [
            {
                "personImage": {"image": {"bytesBase64Encoded": _b64.b64encode(person_bytes).decode("utf-8")}},
                "productImages": [
                    {"image": {"bytesBase64Encoded": _b64.b64encode(garment_bytes).decode("utf-8")}}
                ],
            }
        ],
        "parameters": {"sampleCount": 1},
    }

    headers = {"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json; charset=utf-8"}

    # Call REST
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"Vertex VTO HTTP {resp.status_code}: {resp.text}")
        data = resp.json()
        preds = data.get("predictions", [])
        if not preds:
            raise RuntimeError("Vertex VTO returned no predictions")
        img_b64 = preds[0].get("bytesBase64Encoded")
        if not img_b64:
            # Some responses may wrap fields; attempt alternate structure
            img_b64 = preds[0].get("image", {}).get("bytesBase64Encoded")
        if not img_b64:
            raise RuntimeError("Vertex VTO missing bytesBase64Encoded in response")
        return _b64.b64decode(img_b64)
    except Exception as e:
        raise RuntimeError(f"Virtual Try-On API error: {e}")
