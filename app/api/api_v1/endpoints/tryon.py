from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
import base64

router = APIRouter()


@router.post("/tryon")
async def try_on_clothes(person: UploadFile = File(...), garment: UploadFile = File(...)):
    """
    Simple server-side preview: overlays garment image onto person image and returns a base64 PNG.
    This is a placeholder for Vertex AI try-on integration.
    """
    try:
        person_bytes = await person.read()
        garment_bytes = await garment.read()

        # Official Vertex VTO (no fallback)
        from app.services.vertex_tryon_service import generate_vertex_vto
        try:
            out_bytes = await generate_vertex_vto(person_bytes, garment_bytes)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

        data_url = "data:image/png;base64," + base64.b64encode(out_bytes).decode("utf-8")
        return JSONResponse({"resultImageBase64": data_url, "provider": "vertex_vto"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Try-on failed: {e}")
