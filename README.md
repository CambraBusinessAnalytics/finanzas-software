
# Dashboard financiero: Brasil vs Paraguay para empresa de software

Este paquete contiene un dashboard Dash/Plotly editable para comparar:

1. Operar solo en Brasil.
2. Facturar desde una empresa paraguaya a la empresa de Brasil.

## Archivos

- `app.py`: aplicación Dash.
- `requirements.txt`: dependencias.
- `supuestos_base.csv`: supuestos iniciales editables.

## Cómo ejecutar

```bash
pip install -r requirements.txt
python app.py
```

Luego abrir el enlace local que muestra Dash, normalmente `http://127.0.0.1:8050/`.

## Supuestos fiscales cargados

- IRE Paraguay: 10% sobre renta neta.
- IDU a no residentes: 15% sobre utilidades/dividendos distribuidos.
- IPS patronal: 16,5% sobre salarios en relación de dependencia.
- Aguinaldo: 1 salario adicional anual, modelado como 1/12 de salarios anuales.
- IVA de egresos: configurable. Por defecto se trata como costo no recuperable, con 10% general y 10% para alquiler comercial.

## Advertencia de uso

El modelo es financiero y de sensibilidad. El encuadre fiscal definitivo debe ser validado con asesor tributario, especialmente:
- Exportación de servicios desde Paraguay a Brasil.
- IVA crédito fiscal recuperable/no recuperable.
- Precios de transferencia / sustancia económica.
- Tratamiento tributario en Brasil de pagos a Paraguay y recepción de dividendos.
