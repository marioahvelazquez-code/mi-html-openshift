from flask import Flask, request, jsonify
from pathlib import Path
import win32com.client

app = Flask(__name__)

@app.route('/convertir', methods=['POST'])
def convertir():

    data = request.get_json()

    ruta = data.get("ruta")

    if not ruta:
        return jsonify({
            "error": "No se recibió ruta"
        }), 400

    pptx_path = Path(ruta)

    if not pptx_path.exists():
        return jsonify({
            "error": "El archivo no existe"
        }), 404

    pdf_path = pptx_path.with_suffix(".pdf")

    powerpoint = win32com.client.Dispatch("PowerPoint.Application")
    powerpoint.Visible = 1

    try:

        presentation = powerpoint.Presentations.Open(
            str(pptx_path),
            WithWindow=False
        )

        # 32 = PDF
        presentation.SaveAs(str(pdf_path), 32)

        presentation.Close()

    finally:
        powerpoint.Quit()

    return jsonify({
        "pptx": str(pptx_path),
        "pdf": str(pdf_path)
    })

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
    