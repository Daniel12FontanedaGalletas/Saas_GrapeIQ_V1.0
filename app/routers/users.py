# Saas_GrapeIQ_V1.0/app/routers/users.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import shutil
from pathlib import Path

from .. import models
from ..services import security
from ..database import get_db

router = APIRouter(
    prefix="/api/users",
    tags=["Users"],
    responses={404: {"description": "Not found"}},
)

# Directorio para guardar las imágenes de perfil
UPLOAD_DIR = Path("./static/profile_pics")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.get("/me", response_model=models.UserInDB)
async def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    """
    Obtiene la información del usuario actualmente autenticado.
    """
    return current_user

@router.put("/me", response_model=models.UserInDB)
async def update_user_me(
    db: Session = Depends(get_db),
    winery_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Actualiza el nombre de la bodega y la foto de perfil del usuario.
    """
    user_in_db = db.query(models.User).filter(models.User.username == current_user.username).first()
    if not user_in_db:
        raise HTTPException(status_code=404, detail="User not found")

    # Actualizar nombre de la bodega
    user_in_db.winery_name = winery_name

    # Si se sube un nuevo archivo de imagen
    if file:
        # Generar un nombre de archivo seguro
        file_extension = Path(file.filename).suffix
        new_filename = f"{current_user.username}_{Path(file.filename).stem}{file_extension}"
        file_path = UPLOAD_DIR / new_filename
        
        # Guardar el archivo en el servidor
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Guardar la URL de acceso en la base de datos
        user_in_db.profile_image_url = f"/static/profile_pics/{new_filename}"

    db.commit()
    db.refresh(user_in_db)
    
    return user_in_db