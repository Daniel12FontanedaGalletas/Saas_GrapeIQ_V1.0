# Saas_GrapeIQ_V1.0/app/routers/field_log.py

from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List
from contextlib import closing
import uuid
from datetime import date, datetime
import psycopg2
from fpdf import FPDF
import csv
import io

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/field-logs",
    tags=["Field Logs"],
)

@router.post("/", response_model=schemas.FieldLog, status_code=201)
def create_field_log(
    log: schemas.FieldLogCreate, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    start_datetime = log.log_date
    end_datetime = None
    all_day = True

    if log.start_time:
        start_datetime = datetime.combine(log.log_date, log.start_time.time())
        all_day = False
        if log.end_time:
            end_datetime = datetime.combine(log.log_date, log.end_time.time())

    query = """
        INSERT INTO field_logs (start_datetime, end_datetime, activity_type, description, parcel_id, all_day, tenant_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, start_datetime, end_datetime, activity_type, description, parcel_id, all_day
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # CORRECCIÓN: Convertir el UUID de la parcela a string si existe
                parcel_id_str = str(log.parcel_id) if log.parcel_id else None
                
                cur.execute(query, (
                    start_datetime, end_datetime, log.activity_type, log.description, 
                    parcel_id_str, all_day, str(current_user.tenant_id)
                ))
                rec = cur.fetchone()
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}")
    
    return schemas.FieldLog(
        id=rec[0], start_datetime=rec[1], end_datetime=rec[2], activity_type=rec[3],
        description=rec[4], parcel_id=rec[5], all_day=rec[6]
    )


@router.get("/", response_model=List[schemas.FieldLog])
def get_all_field_logs(current_user: schemas.UserInDB = Depends(security.get_current_active_user)):
    """
    Obtiene todas las entradas del cuaderno de campo para el usuario actual.
    """
    query = """
        SELECT id, start_datetime, end_datetime, activity_type, description, parcel_id, all_day 
        FROM field_logs 
        WHERE tenant_id = %s 
        ORDER BY start_datetime DESC
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id),))
                recs = cur.fetchall()
    except (Exception, psycopg2.Error) as error:
        print(f"Error fetching field logs: {error}")
        raise HTTPException(status_code=500, detail="Error interno al obtener las entradas.")
        
    return [
        schemas.FieldLog(
            id=r[0], start_datetime=r[1], end_datetime=r[2], activity_type=r[3], 
            description=r[4], parcel_id=r[5], all_day=r[6]
        ) for r in recs
    ]


@router.put("/{log_id}", response_model=schemas.FieldLog)
def update_field_log(
    log_id: uuid.UUID,
    log: schemas.FieldLogCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    start_datetime = log.log_date
    end_datetime = None
    all_day = True

    if log.start_time:
        start_datetime = datetime.combine(log.log_date, log.start_time.time())
        all_day = False
        if log.end_time:
            end_datetime = datetime.combine(log.log_date, log.end_time.time())

    query = """
        UPDATE field_logs
        SET start_datetime = %s, end_datetime = %s, activity_type = %s, 
            description = %s, parcel_id = %s, all_day = %s
        WHERE id = %s AND tenant_id = %s
        RETURNING id, start_datetime, end_datetime, activity_type, description, parcel_id, all_day
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # CORRECCIÓN: Convertir el UUID de la parcela a string si existe
                parcel_id_str = str(log.parcel_id) if log.parcel_id else None

                cur.execute(query, (
                    start_datetime, end_datetime, log.activity_type, log.description,
                    parcel_id_str, all_day, str(log_id), str(current_user.tenant_id)
                ))
                rec = cur.fetchone()
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}")

    if not rec:
        raise HTTPException(status_code=404, detail="Log entry not found")
        
    return schemas.FieldLog(
        id=rec[0], start_datetime=rec[1], end_datetime=rec[2], activity_type=rec[3],
        description=rec[4], parcel_id=rec[5], all_day=rec[6]
    )

@router.delete("/{log_id}", status_code=204)
def delete_field_log(
    log_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM field_logs WHERE id = %s AND tenant_id = %s",
                    (str(log_id), str(current_user.tenant_id))
                )
                conn.commit()
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}")
    return

@router.get("/export/")
def export_field_logs(
    start_date: date, 
    end_date: date, 
    format: str, 
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    query = """
        SELECT fl.start_datetime, fl.activity_type, p.name as parcel_name, fl.description
        FROM field_logs fl
        LEFT JOIN parcels p ON fl.parcel_id = p.id
        WHERE fl.tenant_id = %s AND fl.start_datetime::date BETWEEN %s AND %s
        ORDER BY fl.start_datetime
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (str(current_user.tenant_id), start_date, end_date))
                recs = cur.fetchall()
    except (Exception, psycopg2.Error) as error:
        raise HTTPException(status_code=500, detail=f"Database error: {error}")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Fecha", "Actividad", "Parcela", "Descripción"])
        for rec in recs:
            writer.writerow([rec[0].strftime("%Y-%m-%d %H:%M"), rec[1], rec[2] or '', rec[3] or ''])
        return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=cuaderno_de_campo.csv"})

    elif format == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Cuaderno de Campo", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        
        pdf.cell(40, 10, 'Fecha', 1)
        pdf.cell(60, 10, 'Actividad', 1)
        pdf.cell(40, 10, 'Parcela', 1)
        pdf.cell(50, 10, 'Descripción', 1)
        pdf.ln()

        for rec in recs:
            pdf.cell(40, 10, rec[0].strftime("%Y-%m-%d %H:%M"), 1)
            pdf.cell(60, 10, rec[1], 1)
            pdf.cell(40, 10, rec[2] or '', 1)
            pdf.cell(50, 10, rec[3] or '', 1)
            pdf.ln()

        return Response(content=pdf.output(dest='S').encode('latin-1'), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=cuaderno_de_campo.pdf"})

    raise HTTPException(status_code=400, detail="Invalid format specified")