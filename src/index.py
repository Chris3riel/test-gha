from fastapi import FastAPI, UploadFile, File, HTTPException
import sqlite3
import pytesseract
from pdf2image import convert_from_bytes
import os
import shutil
import json
from datetime import datetime

app = FastAPI()

# Configuración de la base de datos
DB_NAME = "./data/db/tickets.db"
UPLOAD_FOLDER = "./data/facturas"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nombre_empresa TEXT,
                        folio TEXT,
                        fecha_ticket TEXT,
                        total_compra REAL,
                        tipo_pago TEXT,
                        iva REAL,
                        ieps REAL,
                        otros_impuestos REAL,
                        archivo_pdf TEXT
                    )"""
    )
    conn.commit()
    conn.close()


init_db()


@app.post("/upload/")
async def upload_ticket(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    data = process_ticket(file_location)
    if data:
        save_to_db(data, file_location)
        return {"message": "Archivo procesado exitosamente", "data": data}
    else:
        raise HTTPException(
            status_code=400, detail="No se pudieron extraer datos válidos del ticket"
        )


def process_ticket(file_path):
    images = convert_from_bytes(open(file_path, "rb").read())
    text = "\n".join([pytesseract.image_to_string(img) for img in images])

    data = extract_data(text)
    return data


def extract_data(text):
    try:
        lines = text.split("\n")
        nombre_empresa = lines[0] if lines else "Desconocido"
        fecha_ticket = None
        folio = None
        total_compra = None
        tipo_pago = "Desconocido"
        iva, ieps, otros_impuestos = 0.0, 0.0, 0.0

        for line in lines:
            if "Fecha" in line:
                fecha_ticket = line.split()[-1]
            elif "Folio" in line:
                folio = line.split()[-1]
            elif "Total" in line:
                total_compra = float(line.split()[-1].replace("$", "").replace(",", ""))
            elif "IVA" in line:
                iva = float(line.split()[-1].replace("$", "").replace(",", ""))
            elif "IEPS" in line:
                ieps = float(line.split()[-1].replace("$", "").replace(",", ""))

        return {
            "nombre_empresa": nombre_empresa,
            "folio": folio,
            "fecha_ticket": fecha_ticket,
            "total_compra": total_compra,
            "tipo_pago": tipo_pago,
            "iva": iva,
            "ieps": ieps,
            "otros_impuestos": otros_impuestos,
        }
    except:
        return None


def save_to_db(data, file_path):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO tickets (nombre_empresa, folio, fecha_ticket, total_compra, tipo_pago, iva, ieps, otros_impuestos, archivo_pdf)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data["nombre_empresa"],
            data["folio"],
            data["fecha_ticket"],
            data["total_compra"],
            data["tipo_pago"],
            data["iva"],
            data["ieps"],
            data["otros_impuestos"],
            file_path,
        ),
    )
    conn.commit()
    conn.close()


@app.get("/tickets/")
def get_tickets():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets")
    tickets = cursor.fetchall()
    conn.close()
    return {"tickets": tickets}


@app.get("/export/csv/")
def export_csv():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets")
    tickets = cursor.fetchall()
    conn.close()

    csv_data = "id,nombre_empresa,folio,fecha_ticket,total_compra,tipo_pago,iva,ieps,otros_impuestos,archivo_pdf\n"
    for ticket in tickets:
        csv_data += ",".join(map(str, ticket)) + "\n"

    return {"csv": csv_data}
