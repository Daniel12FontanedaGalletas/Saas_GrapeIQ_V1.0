# Saas_GrapeIQ_V1.0/app/routers/field_log.py

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import date, datetime, timedelta
from contextlib import closing
import uuid
import io # <-- ¡ESTA ES LA LÍNEA QUE FALTABA!
import csv
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from .. import schemas
from ..services import security
from ..database import get_db_connection

router = APIRouter(
    prefix="/api/field-logs",
    tags=["Field Logs"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.FieldLog, status_code=201)
def create_field_log(
    log: schemas.FieldLogCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    all_day = log.start_time is None
    
    if all_day:
        start_datetime = datetime.combine(log.log_date, datetime.min.time())
        end_datetime = None # Para eventos de todo el día, FullCalendar no necesita hora de fin
    else:
        start_datetime = datetime.combine(log.log_date, log.start_time)
        # Si no se especifica hora de fin, asumimos que dura 1 hora.
        end_datetime = datetime.combine(log.log_date, log.end_time) if log.end_time else start_datetime + timedelta(hours=1)

    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    INSERT INTO field_logs (start_datetime, end_datetime, activity_type, description, plot_name, all_day, tenant_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, start_datetime, end_datetime, activity_type, description, plot_name, all_day
                    """,
                    (start_datetime, end_datetime, log.activity_type, log.description, log.plot_name, all_day, str(current_user.tenant_id))
                )
                new_log_record = cur.fetchone()
                conn.commit()
        
        return schemas.FieldLog(
            id=new_log_record[0],
            start_datetime=new_log_record[1],
            end_datetime=new_log_record[2],
            activity_type=new_log_record[3],
            description=new_log_record[4],
            plot_name=new_log_record[5],
            all_day=new_log_record[6]
        )
    except Exception as e:
        print(f"Error al crear la entrada del cuaderno de campo: {e}")
        raise HTTPException(status_code=500, detail="Error interno al guardar la entrada.")


@router.get("/", response_model=List[schemas.FieldLog])
def get_field_logs(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                query = "SELECT id, start_datetime, end_datetime, activity_type, description, plot_name, all_day FROM field_logs WHERE tenant_id = %s"
                params = [str(current_user.tenant_id)]

                if start_date:
                    query += " AND start_datetime >= %s"
                    params.append(start_date)
                if end_date:
                    # Ajustamos para incluir todo el día en la fecha de fin
                    query += " AND start_datetime < %s"
                    params.append(end_date + timedelta(days=1))
                
                query += " ORDER BY start_datetime DESC"

                cur.execute(query, tuple(params))
                logs_records = cur.fetchall()

        logs = [
            schemas.FieldLog(id=rec[0], start_datetime=rec[1], end_datetime=rec[2], activity_type=rec[3], description=rec[4], plot_name=rec[5], all_day=rec[6])
            for rec in logs_records
        ]
        return logs
    except Exception as e:
        print(f"Error al obtener las entradas del cuaderno de campo: {e}")
        raise HTTPException(status_code=500, detail="Error interno al obtener las entradas.")
    
@router.delete("/{log_id}", status_code=204)
def delete_field_log(
    log_id: uuid.UUID,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Elimina una entrada del cuaderno de campo por su ID,
    asegurándose de que pertenezca al usuario actual.
    """
    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                # Ejecutamos el DELETE y pedimos que nos devuelva el ID si tuvo éxito
                cur.execute(
                    """
                    DELETE FROM field_logs
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id
                    """,
                    (str(log_id), str(current_user.tenant_id))
                )
                deleted_id = cur.fetchone()
                conn.commit()
        
        # Si no se devolvió ningún ID, significa que el registro no existía o no pertenecía al usuario
        if not deleted_id:
            raise HTTPException(status_code=404, detail="Entrada no encontrada o no tienes permiso para eliminarla.")
        
        # No devolvemos contenido, el código 204 se encarga de eso.
        return

    except Exception as e:
        print(f"Error al eliminar la entrada del cuaderno de campo: {e}")
        raise HTTPException(status_code=500, detail="Error interno al eliminar la entrada.")
    
@router.put("/{log_id}", response_model=schemas.FieldLog)
def update_field_log(
    log_id: uuid.UUID,
    log: schemas.FieldLogCreate,
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Actualiza una entrada existente en el cuaderno de campo.
    """
    all_day = log.start_time is None
    if all_day:
        start_datetime = datetime.combine(log.log_date, datetime.min.time())
        end_datetime = None
    else:
        start_datetime = datetime.combine(log.log_date, log.start_time)
        end_datetime = datetime.combine(log.log_date, log.end_time) if log.end_time else start_datetime + timedelta(hours=1)

    try:
        with get_db_connection() as conn:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    """
                    UPDATE field_logs
                    SET start_datetime = %s, end_datetime = %s, activity_type = %s, 
                        description = %s, plot_name = %s, all_day = %s
                    WHERE id = %s AND tenant_id = %s
                    RETURNING id, start_datetime, end_datetime, activity_type, description, plot_name, all_day
                    """,
                    (start_datetime, end_datetime, log.activity_type, log.description, log.plot_name, all_day, str(log_id), str(current_user.tenant_id))
                )
                updated_log_record = cur.fetchone()
                conn.commit()

        if not updated_log_record:
            raise HTTPException(status_code=404, detail="Entrada no encontrada o no tienes permiso para editarla.")

        return schemas.FieldLog(
            id=updated_log_record[0],
            start_datetime=updated_log_record[1],
            end_datetime=updated_log_record[2],
            activity_type=updated_log_record[3],
            description=updated_log_record[4],
            plot_name=updated_log_record[5],
            all_day=updated_log_record[6]
        )
    except Exception as e:
        print(f"Error al actualizar la entrada del cuaderno de campo: {e}")
        raise HTTPException(status_code=500, detail="Error interno al actualizar la entrada.")
    
@router.get("/export/", summary="Exporta el cuaderno de campo a CSV o PDF")
def export_field_logs(
    start_date: date,
    end_date: date,
    format: str, # 'csv' o 'pdf'
    current_user: schemas.UserInDB = Depends(security.get_current_active_user)
):
    """
    Genera un archivo CSV o PDF con los registros del cuaderno de campo
    dentro de un rango de fechas específico, formateado según la normativa.
    """
    logs = get_field_logs(start_date=start_date, end_date=end_date, current_user=current_user)

    if format.lower() == 'csv':
        # La exportación a CSV mantiene su estructura simple pero funcional
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Hora Inicio', 'Hora Fin', 'Actividad', 'Parcela', 'Descripción'])
        
        for log in logs:
            start_time = log.start_datetime.strftime('%H:%M') if not log.all_day else 'Todo el día'
            end_time = log.end_datetime.strftime('%H:%M') if log.end_datetime and not log.all_day else ''
            writer.writerow([
                log.start_datetime.strftime('%Y-%m-%d'),
                start_time,
                end_time,
                log.activity_type,
                log.plot_name or '',
                log.description or ''
            ])
        
        output.seek(0)
        filename = f"cuaderno_de_campo_{start_date}_a_{end_date}.csv"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return StreamingResponse(output, media_type="text/csv", headers=headers)

    elif format.lower() == 'pdf':
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        
        elements = []
        
        # --- 1. Portada del Documento ---
        elements.append(Paragraph("CUADERNO DE EXPLOTACIÓN AGRÍCOLA", styles['h1']))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Periodo del informe: {start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}", styles['h2']))
        elements.append(Spacer(1, 1*inch))
        
        # --- 2. Datos de la Explotación (con placeholders) ---
        elements.append(Paragraph("DATOS GENERALES DE LA EXPLOTACIÓN", styles['h3']))
        
        # A futuro, estos datos vendrán de la base de datos (tabla tenants o users)
        titular_data = [
            ["RAZÓN SOCIAL / NOMBRE:", current_user.username],
            ["NIF:", "[Dato no disponible]"],
            ["DOMICILIO:", "[Dato no disponible]"],
            ["CÓDIGO REA:", "[Dato no disponible]"]
        ]
        titular_table = Table(titular_data, colWidths=[2*inch, 5*inch])
        titular_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(titular_table)
        elements.append(PageBreak())

        # --- 3. Tabla de Actuaciones ---
        elements.append(Paragraph("REGISTRO DE ACTUACIONES", styles['h2']))
        elements.append(Spacer(1, 0.2*inch))

        # Separamos tratamientos fitosanitarios del resto para un formato más detallado
        tratamientos = [log for log in logs if log.activity_type == 'Tratamiento Fitosanitario']
        otras_actividades = [log for log in logs if log.activity_type != 'Tratamiento Fitosanitario']
        
        # Tabla para tratamientos fitosanitarios (formato oficial)
        if tratamientos:
            elements.append(Paragraph("Tratamientos Fitosanitarios", styles['h3']))
            data_tratamientos = [['Fecha', 'Parcela', 'Actividad', 'Producto (Nº Reg.)', 'Dosis', 'Justificación']]
            for log in tratamientos:
                # A futuro, estos detalles se guardarían en campos separados
                data_tratamientos.append([
                    log.start_datetime.strftime('%d/%m/%Y'),
                    log.plot_name or '',
                    log.activity_type,
                    log.description or "[Producto no especificado]",
                    "[Dosis no especificada]",
                    "[Justificación no especificada]"
                ])
            
            table_trat = Table(data_tratamientos, colWidths=[1*inch, 1.5*inch, 1.5*inch, 2*inch, 1*inch, 2*inch])
            table_trat.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5C1A33')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black), ('WORDWRAP', (0, 0), (-1, -1), 'CJK')
            ]))
            elements.append(table_trat)
            elements.append(Spacer(1, 0.3*inch))

        # Tabla para otras actividades
        if otras_actividades:
            elements.append(Paragraph("Otras Actuaciones (Poda, Riego, Abonado, etc.)", styles['h3']))
            data_otras = [['Fecha', 'Hora', 'Actividad', 'Parcela', 'Descripción']]
            for log in otras_actividades:
                hora = log.start_datetime.strftime('%H:%M') if not log.all_day else 'Todo el día'
                data_otras.append([
                    log.start_datetime.strftime('%d/%m/%Y'),
                    hora,
                    log.activity_type,
                    log.plot_name or '',
                    log.description or ''
                ])

            table_otras = Table(data_otras, colWidths=[1*inch, 1*inch, 1.5*inch, 1.5*inch, 4*inch])
            table_otras.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5C1A33')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12), ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black), ('WORDWRAP', (0, 0), (-1, -1), 'CJK')
            ]))
            elements.append(table_otras)

        if not logs:
            elements.append(Paragraph("No se encontraron registros en el rango de fechas seleccionado.", styles['Normal']))

        doc.build(elements)
        
        buffer.seek(0)
        filename = f"cuaderno_de_campo_{start_date}_a_{end_date}.pdf"
        headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    else:
        raise HTTPException(status_code=400, detail="Formato de exportación no válido. Use 'csv' o 'pdf'.")