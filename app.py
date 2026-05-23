
import os
import math
from dataclasses import dataclass
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table

# ============================================================
# DASHBOARD FINANCIERO: SOFTWARE BRASIL VS PARAGUAY
# Horizonte: 10 años
# Moneda de presentación: BRL
# Los costos locales en PYG se convierten usando PYG por BRL.
# ============================================================

APP_TITLE = "Análisis financiero: operación Brasil vs Paraguay"

DEFAULTS = {
    "years": 10,
    "annual_revenue_brl": 9_500_000,
    "revenue_growth": 0.03,
    "pyg_per_brl": 1450,
    "pyg_per_usd": 7500,
    "inflation_py": 0.04,
    "inflation_br": 0.04,

    # Paraguay - personal
    "employee_count": 8,
    "monthly_salary_pyg": 6_000_000,
    "contractor_count": 0,
    "monthly_contractor_fee_pyg": 7_000_000,
    "use_payroll": True,
    "ips_employer": 0.165,
    "aguinaldo_rate": 1/12,

    # Paraguay - costos fijos
    "monthly_office_rent_pyg": 1_500_000,
    "accounting_monthly_pyg": 4_000_000,
    "advisory_annual_pyg": 24_000_000,
    "regulatory_annual_pyg": 8_000_000,
    "utilities_monthly_pyg": 1_200_000,
    "internet_monthly_pyg": 350_000,
    "phone_monthly_pyg": 250_000,
    "insurance_annual_pyg": 6_000_000,
    "supplies_monthly_pyg": 600_000,
    "software_monthly_pyg": 2_500_000,

    # Inversiones iniciales Paraguay
    "incorporation_usd": 400,
    "invoice_cert_pyg": 480_000,
    "seal_pyg": 130_000,
    "office_setup_pyg": 10_000_000,
    "computer_count": 8,
    "computer_unit_pyg": 3_000_000,

    # Impuestos Paraguay
    "ire_rate": 0.10,
    "idu_nonresident_rate": 0.15,
    "dividend_distribution_rate": 1.00,
    "expense_vat_general": 0.10,
    "rent_vat": 0.10,
    "include_nonrecoverable_vat": True,

    # Brasil baseline editable
    "br_cost_ratio": 0.68,
    "br_fixed_annual_brl": 0,
    "br_effective_tax_rate": 0.24,
}

def brl_from_pyg(value_pyg, pyg_per_brl):
    if pyg_per_brl <= 0:
        return 0
    return value_pyg / pyg_per_brl

def brl_from_usd(value_usd, pyg_per_usd, pyg_per_brl):
    return brl_from_pyg(value_usd * pyg_per_usd, pyg_per_brl)

def fmt_money(x):
    return f"R$ {x:,.0f}".replace(",", ".")

def compute_model(p):
    years = int(p["years"])
    rows = []

    setup_pyg = (
        p["invoice_cert_pyg"] + p["seal_pyg"] + p["office_setup_pyg"] +
        p["computer_count"] * p["computer_unit_pyg"]
    )
    setup_brl = brl_from_pyg(setup_pyg, p["pyg_per_brl"]) + brl_from_usd(
        p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"]
    )

    for y in range(1, years + 1):
        rev_brl = p["annual_revenue_brl"] * ((1 + p["revenue_growth"]) ** (y - 1))
        py_infl = ((1 + p["inflation_py"]) ** (y - 1))
        br_infl = ((1 + p["inflation_br"]) ** (y - 1))

        # Paraguay personnel
        salary_annual_pyg = p["employee_count"] * p["monthly_salary_pyg"] * 12 * py_infl
        contractors_annual_pyg = p["contractor_count"] * p["monthly_contractor_fee_pyg"] * 12 * py_infl

        if p["use_payroll"]:
            aguinaldo_pyg = salary_annual_pyg * p["aguinaldo_rate"]
            ips_pyg = salary_annual_pyg * p["ips_employer"]
        else:
            aguinaldo_pyg = 0
            ips_pyg = 0

        # Paraguay fixed operating costs
        rent_base_pyg = p["monthly_office_rent_pyg"] * 12 * py_infl
        accounting_pyg = p["accounting_monthly_pyg"] * 12 * py_infl
        advisory_pyg = p["advisory_annual_pyg"] * py_infl
        regulatory_pyg = p["regulatory_annual_pyg"] * py_infl
        utilities_pyg = p["utilities_monthly_pyg"] * 12 * py_infl
        internet_pyg = p["internet_monthly_pyg"] * 12 * py_infl
        phone_pyg = p["phone_monthly_pyg"] * 12 * py_infl
        insurance_pyg = p["insurance_annual_pyg"] * py_infl
        supplies_pyg = p["supplies_monthly_pyg"] * 12 * py_infl
        software_pyg = p["software_monthly_pyg"] * 12 * py_infl

        taxable_expenses_pyg = (
            accounting_pyg + advisory_pyg + regulatory_pyg + utilities_pyg +
            internet_pyg + phone_pyg + insurance_pyg + supplies_pyg + software_pyg +
            contractors_annual_pyg
        )

        nonrecoverable_vat_pyg = 0
        if p["include_nonrecoverable_vat"]:
            nonrecoverable_vat_pyg = taxable_expenses_pyg * p["expense_vat_general"] + rent_base_pyg * p["rent_vat"]

        opex_pyg = (
            salary_annual_pyg + contractors_annual_pyg + aguinaldo_pyg + ips_pyg +
            rent_base_pyg + accounting_pyg + advisory_pyg + regulatory_pyg +
            utilities_pyg + internet_pyg + phone_pyg + insurance_pyg +
            supplies_pyg + software_pyg + nonrecoverable_vat_pyg
        )

        opex_brl = brl_from_pyg(opex_pyg, p["pyg_per_brl"])
        capex_brl = setup_brl if y == 1 else 0
        ebit_pre_tax_brl = rev_brl - opex_brl - capex_brl
        ire_brl = max(0, ebit_pre_tax_brl * p["ire_rate"])
        profit_after_ire_brl = ebit_pre_tax_brl - ire_brl
        idu_brl = max(0, profit_after_ire_brl * p["dividend_distribution_rate"] * p["idu_nonresident_rate"])
        net_remitted_brl = profit_after_ire_brl - idu_brl

        # Brazil baseline
        br_costs_brl = rev_brl * p["br_cost_ratio"] + p["br_fixed_annual_brl"] * br_infl
        br_profit_pre_tax = rev_brl - br_costs_brl
        br_tax = max(0, br_profit_pre_tax * p["br_effective_tax_rate"])
        br_net = br_profit_pre_tax - br_tax

        rows.append({
            "Año": y,
            "Ingresos BRL": rev_brl,
            "PY OPEX BRL": opex_brl,
            "PY CAPEX BRL": capex_brl,
            "PY IRE BRL": ire_brl,
            "PY IDU BRL": idu_brl,
            "PY Resultado Neto Remitible BRL": net_remitted_brl,
            "BR Costos BRL": br_costs_brl,
            "BR Impuestos BRL": br_tax,
            "BR Resultado Neto BRL": br_net,
            "Diferencia PY - BR BRL": net_remitted_brl - br_net,
            "PY Margen Neto": net_remitted_brl / rev_brl if rev_brl else 0,
            "BR Margen Neto": br_net / rev_brl if rev_brl else 0,
            "PY IVA no recuperable BRL": brl_from_pyg(nonrecoverable_vat_pyg, p["pyg_per_brl"]),
            "PY Servicios personales BRL": brl_from_pyg(salary_annual_pyg + contractors_annual_pyg + aguinaldo_pyg + ips_pyg, p["pyg_per_brl"]),
            "PY Servicios no personales BRL": brl_from_pyg(rent_base_pyg + accounting_pyg + advisory_pyg + regulatory_pyg + utilities_pyg + internet_pyg + phone_pyg + insurance_pyg + software_pyg, p["pyg_per_brl"]),
            "PY Bienes consumo e insumos BRL": brl_from_pyg(supplies_pyg, p["pyg_per_brl"]),
            "PY Impuestos tasas contribuciones BRL": ire_brl + idu_brl + brl_from_pyg(nonrecoverable_vat_pyg, p["pyg_per_brl"]),
        })

    return pd.DataFrame(rows)

def input_number(label, id_, value, step=1, min_=0, suffix=None):
    return dbc.Col([
        dbc.Label(label, className="small fw-semibold"),
        dbc.InputGroup([
            dbc.Input(id=id_, type="number", value=value, step=step, min=min_),
            dbc.InputGroupText(suffix) if suffix else html.Span()
        ])
    ], md=3, sm=6, xs=12, className="mb-3")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

controls = dbc.Card([
    dbc.CardHeader(html.H5("Calculadora de supuestos", className="m-0")),
    dbc.CardBody([
        html.H6("Ingresos y tipo de cambio"),
        dbc.Row([
            input_number("Facturación anual", "annual_revenue_brl", DEFAULTS["annual_revenue_brl"], 100000, 0, "BRL"),
            input_number("Crecimiento anual ingresos", "revenue_growth", DEFAULTS["revenue_growth"]*100, 0.5, -100, "%"),
            input_number("PYG por BRL", "pyg_per_brl", DEFAULTS["pyg_per_brl"], 10, 1),
            input_number("PYG por USD", "pyg_per_usd", DEFAULTS["pyg_per_usd"], 10, 1),
        ]),
        html.Hr(),
        html.H6("Servicios personales Paraguay"),
        dbc.Row([
            input_number("Funcionarios", "employee_count", DEFAULTS["employee_count"], 1, 0),
            input_number("Salario mensual por funcionario", "monthly_salary_pyg", DEFAULTS["monthly_salary_pyg"], 100000, 0, "PYG"),
            input_number("Prestadores PJ", "contractor_count", DEFAULTS["contractor_count"], 1, 0),
            input_number("Fee mensual PJ", "monthly_contractor_fee_pyg", DEFAULTS["monthly_contractor_fee_pyg"], 100000, 0, "PYG"),
            input_number("IPS patronal", "ips_employer", DEFAULTS["ips_employer"]*100, 0.1, 0, "%"),
        ]),
        dbc.Checklist(
            options=[{"label": "Incluir aguinaldo e IPS para funcionarios en relación de dependencia", "value": 1}],
            value=[1],
            id="use_payroll",
            switch=True,
            className="mb-2"
        ),
        html.Hr(),
        html.H6("Servicios no personales y costos operativos Paraguay"),
        dbc.Row([
            input_number("Alquiler oficina mensual", "monthly_office_rent_pyg", DEFAULTS["monthly_office_rent_pyg"], 100000, 0, "PYG"),
            input_number("Contabilidad mensual", "accounting_monthly_pyg", DEFAULTS["accounting_monthly_pyg"], 100000, 0, "PYG"),
            input_number("Asesorías anuales", "advisory_annual_pyg", DEFAULTS["advisory_annual_pyg"], 100000, 0, "PYG"),
            input_number("Regulatorios anuales", "regulatory_annual_pyg", DEFAULTS["regulatory_annual_pyg"], 100000, 0, "PYG"),
            input_number("Electricidad/servicios mensual", "utilities_monthly_pyg", DEFAULTS["utilities_monthly_pyg"], 50000, 0, "PYG"),
            input_number("Internet mensual", "internet_monthly_pyg", DEFAULTS["internet_monthly_pyg"], 50000, 0, "PYG"),
            input_number("Telefonía mensual", "phone_monthly_pyg", DEFAULTS["phone_monthly_pyg"], 50000, 0, "PYG"),
            input_number("Seguros anuales", "insurance_annual_pyg", DEFAULTS["insurance_annual_pyg"], 100000, 0, "PYG"),
            input_number("Librería/papelería mensual", "supplies_monthly_pyg", DEFAULTS["supplies_monthly_pyg"], 50000, 0, "PYG"),
            input_number("Software mensual", "software_monthly_pyg", DEFAULTS["software_monthly_pyg"], 100000, 0, "PYG"),
        ]),
        html.Hr(),
        html.H6("Bienes de capital y apertura"),
        dbc.Row([
            input_number("Constitución EAS", "incorporation_usd", DEFAULTS["incorporation_usd"], 10, 0, "USD"),
            input_number("Certificado facturación electrónica", "invoice_cert_pyg", DEFAULTS["invoice_cert_pyg"], 10000, 0, "PYG"),
            input_number("Sello societario", "seal_pyg", DEFAULTS["seal_pyg"], 10000, 0, "PYG"),
            input_number("Mobiliario/oficina inicial", "office_setup_pyg", DEFAULTS["office_setup_pyg"], 100000, 0, "PYG"),
            input_number("Cantidad computadoras", "computer_count", DEFAULTS["computer_count"], 1, 0),
            input_number("Costo unitario computadora", "computer_unit_pyg", DEFAULTS["computer_unit_pyg"], 100000, 0, "PYG"),
        ]),
        html.Hr(),
        html.H6("Impuestos Paraguay"),
        dbc.Row([
            input_number("IRE", "ire_rate", DEFAULTS["ire_rate"]*100, 0.1, 0, "%"),
            input_number("IDU no residente", "idu_nonresident_rate", DEFAULTS["idu_nonresident_rate"]*100, 0.1, 0, "%"),
            input_number("% utilidad distribuida", "dividend_distribution_rate", DEFAULTS["dividend_distribution_rate"]*100, 1, 0, "%"),
            input_number("IVA gastos generales", "expense_vat_general", DEFAULTS["expense_vat_general"]*100, 0.1, 0, "%"),
            input_number("IVA alquiler comercial", "rent_vat", DEFAULTS["rent_vat"]*100, 0.1, 0, "%"),
        ]),
        dbc.Checklist(
            options=[{"label": "Tratar IVA crédito de egresos como costo no recuperable", "value": 1}],
            value=[1],
            id="include_nonrecoverable_vat",
            switch=True,
            className="mb-2"
        ),
        html.Hr(),
        html.H6("Escenario Brasil actual / baseline"),
        dbc.Row([
            input_number("Costo operativo Brasil / ingresos", "br_cost_ratio", DEFAULTS["br_cost_ratio"]*100, 1, 0, "%"),
            input_number("Costo fijo anual adicional Brasil", "br_fixed_annual_brl", DEFAULTS["br_fixed_annual_brl"], 100000, 0, "BRL"),
            input_number("Tasa efectiva impuesto Brasil", "br_effective_tax_rate", DEFAULTS["br_effective_tax_rate"]*100, 0.5, 0, "%"),
            input_number("Inflación costos Paraguay", "inflation_py", DEFAULTS["inflation_py"]*100, 0.5, 0, "%"),
            input_number("Inflación costos Brasil", "inflation_br", DEFAULTS["inflation_br"]*100, 0.5, 0, "%"),
        ]),
    ])
], className="shadow-sm mb-4")

app.layout = html.Div([
    html.Header(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1(APP_TITLE, className="m-0", style={
                        "fontFamily": "Avenir, Arial, sans-serif",
                        "fontWeight": "700",
                        "fontSize": "2rem",
                        "color": "#333"
                    }),
                    html.P("Modelo editable de 10 años para comparar resultado neto de operar en Brasil vs estructurar operación en Paraguay.",
                           className="text-muted mb-0")
                ], md=10)
            ], justify="center", className="py-4")
        ]),
        style={"backgroundColor": "white", "borderBottom": "1px solid #eee"}
    ),
    dbc.Container([
        dbc.Alert(
            "Nota: este modelo es una herramienta de análisis financiero. Validar el encuadre fiscal final con contador/abogado tributario, especialmente IVA exportación de servicios, precios de transferencia y retención/tributación en Brasil.",
            color="warning",
            className="mt-3"
        ),
        controls,
        dbc.Row(id="kpi_cards", className="g-3 mb-4"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="net_result_chart"), md=7),
            dbc.Col(dcc.Graph(id="difference_chart"), md=5),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="cost_breakdown_chart"), md=6),
            dbc.Col(dcc.Graph(id="tax_chart"), md=6),
        ]),
        html.H4("Tabla del modelo", className="mt-4"),
        dash_table.DataTable(
            id="model_table",
            page_size=10,
            sort_action="native",
            filter_action="native",
            style_table={"overflowX": "auto"},
            style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px"},
            style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
        ),
        dcc.Download(id="download_model"),
        dbc.Button("Descargar CSV del escenario", id="download_btn", color="primary", className="my-3"),
    ], fluid=True)
], style={"backgroundColor": "#f7f8fa", "minHeight": "100vh"})

def collect_params(*values):
    keys = [
        "annual_revenue_brl", "revenue_growth", "pyg_per_brl", "pyg_per_usd",
        "employee_count", "monthly_salary_pyg", "contractor_count", "monthly_contractor_fee_pyg",
        "ips_employer", "use_payroll",
        "monthly_office_rent_pyg", "accounting_monthly_pyg", "advisory_annual_pyg", "regulatory_annual_pyg",
        "utilities_monthly_pyg", "internet_monthly_pyg", "phone_monthly_pyg", "insurance_annual_pyg",
        "supplies_monthly_pyg", "software_monthly_pyg",
        "incorporation_usd", "invoice_cert_pyg", "seal_pyg", "office_setup_pyg",
        "computer_count", "computer_unit_pyg",
        "ire_rate", "idu_nonresident_rate", "dividend_distribution_rate", "expense_vat_general", "rent_vat",
        "include_nonrecoverable_vat",
        "br_cost_ratio", "br_fixed_annual_brl", "br_effective_tax_rate", "inflation_py", "inflation_br"
    ]
    p = DEFAULTS.copy()
    for k, v in zip(keys, values):
        if k in ["use_payroll", "include_nonrecoverable_vat"]:
            p[k] = bool(v)
        elif k in ["revenue_growth", "ips_employer", "ire_rate", "idu_nonresident_rate", "dividend_distribution_rate", "expense_vat_general", "rent_vat", "br_cost_ratio", "br_effective_tax_rate", "inflation_py", "inflation_br"]:
            p[k] = (v or 0) / 100
        else:
            p[k] = v or 0
    p["years"] = 10
    p["aguinaldo_rate"] = 1/12
    return p

inputs = [
    Input("annual_revenue_brl", "value"), Input("revenue_growth", "value"), Input("pyg_per_brl", "value"), Input("pyg_per_usd", "value"),
    Input("employee_count", "value"), Input("monthly_salary_pyg", "value"), Input("contractor_count", "value"), Input("monthly_contractor_fee_pyg", "value"),
    Input("ips_employer", "value"), Input("use_payroll", "value"),
    Input("monthly_office_rent_pyg", "value"), Input("accounting_monthly_pyg", "value"), Input("advisory_annual_pyg", "value"), Input("regulatory_annual_pyg", "value"),
    Input("utilities_monthly_pyg", "value"), Input("internet_monthly_pyg", "value"), Input("phone_monthly_pyg", "value"), Input("insurance_annual_pyg", "value"),
    Input("supplies_monthly_pyg", "value"), Input("software_monthly_pyg", "value"),
    Input("incorporation_usd", "value"), Input("invoice_cert_pyg", "value"), Input("seal_pyg", "value"), Input("office_setup_pyg", "value"),
    Input("computer_count", "value"), Input("computer_unit_pyg", "value"),
    Input("ire_rate", "value"), Input("idu_nonresident_rate", "value"), Input("dividend_distribution_rate", "value"), Input("expense_vat_general", "value"), Input("rent_vat", "value"),
    Input("include_nonrecoverable_vat", "value"),
    Input("br_cost_ratio", "value"), Input("br_fixed_annual_brl", "value"), Input("br_effective_tax_rate", "value"), Input("inflation_py", "value"), Input("inflation_br", "value"),
]

@app.callback(
    Output("kpi_cards", "children"),
    Output("net_result_chart", "figure"),
    Output("difference_chart", "figure"),
    Output("cost_breakdown_chart", "figure"),
    Output("tax_chart", "figure"),
    Output("model_table", "data"),
    Output("model_table", "columns"),
    *inputs
)
def update_dashboard(*values):
    p = collect_params(*values)
    df = compute_model(p)

    total_py = df["PY Resultado Neto Remitible BRL"].sum()
    total_br = df["BR Resultado Neto BRL"].sum()
    total_diff = df["Diferencia PY - BR BRL"].sum()
    y1_diff = df.loc[df["Año"] == 1, "Diferencia PY - BR BRL"].iloc[0]

    def kpi(title, value, subtitle="", color="primary"):
        return dbc.Col(dbc.Card(dbc.CardBody([
            html.Div(title, className="text-muted small"),
            html.H3(value, className="mb-1"),
            html.Div(subtitle, className="small text-muted")
        ]), className="shadow-sm border-0"), md=3, sm=6)

    cards = [
        kpi("Resultado PY acumulado", fmt_money(total_py), "10 años"),
        kpi("Resultado BR acumulado", fmt_money(total_br), "10 años"),
        kpi("Diferencia acumulada", fmt_money(total_diff), "Paraguay - Brasil", "success" if total_diff >= 0 else "danger"),
        kpi("Diferencia año 1", fmt_money(y1_diff), "Paraguay - Brasil"),
    ]

    long_net = df.melt(
        id_vars="Año",
        value_vars=["PY Resultado Neto Remitible BRL", "BR Resultado Neto BRL"],
        var_name="Escenario",
        value_name="Resultado neto BRL"
    )
    fig_net = px.line(long_net, x="Año", y="Resultado neto BRL", color="Escenario", markers=True,
                      template="plotly_white", title="Resultado neto anual por escenario")
    fig_net.update_layout(legend_title_text="", yaxis_tickprefix="R$ ", title_font=dict(size=18))

    fig_diff = px.bar(df, x="Año", y="Diferencia PY - BR BRL", template="plotly_white",
                      title="Ahorro / mejora anual de Paraguay vs Brasil")
    fig_diff.update_layout(yaxis_tickprefix="R$ ", title_font=dict(size=18))

    cost_cols = [
        "PY Servicios personales BRL",
        "PY Servicios no personales BRL",
        "PY Bienes consumo e insumos BRL",
        "PY CAPEX BRL",
        "PY IVA no recuperable BRL"
    ]
    cost_long = df.melt(id_vars="Año", value_vars=cost_cols, var_name="Rubro", value_name="BRL")
    fig_cost = px.area(cost_long, x="Año", y="BRL", color="Rubro", template="plotly_white",
                       title="Estructura de costos Paraguay")
    fig_cost.update_layout(legend_title_text="", yaxis_tickprefix="R$ ", title_font=dict(size=18))

    tax_long = df.melt(id_vars="Año", value_vars=["PY IRE BRL", "PY IDU BRL", "BR Impuestos BRL"],
                       var_name="Impuesto", value_name="BRL")
    fig_tax = px.bar(tax_long, x="Año", y="BRL", color="Impuesto", barmode="group", template="plotly_white",
                     title="Carga tributaria comparada")
    fig_tax.update_layout(legend_title_text="", yaxis_tickprefix="R$ ", title_font=dict(size=18))

    table_df = df.copy()
    for col in table_df.columns:
        if col != "Año":
            if "Margen" in col:
                table_df[col] = (table_df[col] * 100).round(2).astype(str) + "%"
            else:
                table_df[col] = table_df[col].round(0).astype(int)
    columns = [{"name": c, "id": c} for c in table_df.columns]
    return cards, fig_net, fig_diff, fig_cost, fig_tax, table_df.to_dict("records"), columns

@app.callback(
    Output("download_model", "data"),
    Input("download_btn", "n_clicks"),
    *[State(i.component_id, i.component_property) for i in inputs],
    prevent_initial_call=True
)
def download_csv(n_clicks, *values):
    p = collect_params(*values)
    df = compute_model(p)
    return dcc.send_data_frame(df.to_csv, "modelo_brasil_vs_paraguay.csv", index=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
