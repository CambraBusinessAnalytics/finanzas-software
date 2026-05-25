import os
import pandas as pd
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table

# ============================================================
# DASHBOARD FINANCIERO: OPERACIÓN PARAGUAY
# Horizonte editable
# Moneda base de cálculo: BRL para ingresos / PYG para costos locales.
# Moneda de presentación: seleccionable BRL o PYG.
# ============================================================

APP_TITLE = "Análisis financiero: operación en Paraguay"

DEFAULTS = {
    "years": 10,
    "annual_revenue_brl": 9_500_000,
    "revenue_growth": 0.03,
    "pyg_per_brl": 1150,
    "pyg_per_usd": 6100,
    "inflation_py": 0.04,

    # Paraguay - personal
    "employee_count": 3,
    "monthly_salary_pyg": 3_000_000,
    "contractor_count": 1,
    "monthly_contractor_fee_pyg": 7_000_000,
    "use_payroll": True,
    "ips_employer": 0.165,
    "aguinaldo_rate": 1 / 12,

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
    "computer_count": 4,
    "computer_unit_pyg": 3_000_000,

    # Impuestos Paraguay
    "ire_rate": 0.10,
    "idu_nonresident_rate": 0.15,
    "dividend_distribution_rate": 1.00,
    "expense_vat_general": 0.10,
    "rent_vat": 0.10,
}


def brl_from_pyg(value_pyg, pyg_per_brl):
    if pyg_per_brl <= 0:
        return 0
    return value_pyg / pyg_per_brl


def brl_from_usd(value_usd, pyg_per_usd, pyg_per_brl):
    return brl_from_pyg(value_usd * pyg_per_usd, pyg_per_brl)


def convert_from_brl(value_brl, currency, pyg_per_brl):
    if currency == "PYG":
        return value_brl * pyg_per_brl
    return value_brl


def currency_label(currency):
    return "Gs." if currency == "PYG" else "R$"


def fmt_money_brl(x):
    return f"R$ {x:,.0f}".replace(",", ".")


def fmt_money_dynamic(x_brl, currency, pyg_per_brl):
    value = convert_from_brl(x_brl, currency, pyg_per_brl)
    if currency == "PYG":
        return f"Gs. {value:,.0f}".replace(",", ".")
    return f"R$ {value:,.0f}".replace(",", ".")


def compute_model(p):
    years = max(1, int(p["years"]))
    rows = []

    setup_pyg = (
        p["invoice_cert_pyg"]
        + p["seal_pyg"]
        + p["office_setup_pyg"]
        + p["computer_count"] * p["computer_unit_pyg"]
    )
    setup_brl = brl_from_pyg(setup_pyg, p["pyg_per_brl"]) + brl_from_usd(
        p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"]
    )

    for y in range(1, years + 1):
        rev_brl = p["annual_revenue_brl"] * ((1 + p["revenue_growth"]) ** (y - 1))
        py_infl = (1 + p["inflation_py"]) ** (y - 1)

        # Servicios personales
        salary_annual_pyg = p["employee_count"] * p["monthly_salary_pyg"] * 12 * py_infl
        contractors_annual_pyg = p["contractor_count"] * p["monthly_contractor_fee_pyg"] * 12 * py_infl

        if p["use_payroll"]:
            aguinaldo_pyg = salary_annual_pyg * p["aguinaldo_rate"]
            ips_pyg = salary_annual_pyg * p["ips_employer"]
        else:
            aguinaldo_pyg = 0
            ips_pyg = 0

        # Salarios no generan IVA crédito. Prestadores PJ sí generan IVA crédito.
        personal_pyg = salary_annual_pyg + contractors_annual_pyg + aguinaldo_pyg + ips_pyg
        direct_costs_pyg = personal_pyg + p["software_monthly_pyg"] * 12 * py_infl

        # Servicios no personales y gastos operativos
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

        non_personal_pyg = (
            rent_base_pyg
            + accounting_pyg
            + advisory_pyg
            + regulatory_pyg
            + utilities_pyg
            + internet_pyg
            + phone_pyg
            + insurance_pyg
            + software_pyg
        )
        supplies_total_pyg = supplies_pyg

        # Exportación de servicios: sin IVA débito por ventas.
        # Sí se genera IVA crédito en compras/servicios gravados.
        vat_credit_general_base_pyg = (
            contractors_annual_pyg
            + accounting_pyg
            + advisory_pyg
            + regulatory_pyg
            + utilities_pyg
            + internet_pyg
            + phone_pyg
            + insurance_pyg
            + supplies_pyg
            + software_pyg
        )
        iva_credit_general_pyg = vat_credit_general_base_pyg * p["expense_vat_general"]
        iva_credit_rent_pyg = rent_base_pyg * p["rent_vat"]
        iva_credit_pyg = iva_credit_general_pyg + iva_credit_rent_pyg

        # OPEX no incluye IVA crédito fiscal ni CAPEX.
        opex_pyg = personal_pyg + non_personal_pyg + supplies_total_pyg
        opex_brl = brl_from_pyg(opex_pyg, p["pyg_per_brl"])
        capex_brl = setup_brl if y == 1 else 0

        ebitda_brl = rev_brl - opex_brl
        operating_profit_before_tax_brl = ebitda_brl
        ire_brl = max(0, operating_profit_before_tax_brl * p["ire_rate"])
        profit_after_ire_brl = operating_profit_before_tax_brl - ire_brl
        idu_brl = max(
            0,
            profit_after_ire_brl
            * p["dividend_distribution_rate"]
            * p["idu_nonresident_rate"],
        )
        net_remitted_brl = profit_after_ire_brl - idu_brl
        cash_flow_brl = net_remitted_brl - capex_brl
        total_cash_outflows_brl = opex_brl + capex_brl + ire_brl + idu_brl

        gross_profit_brl = rev_brl - brl_from_pyg(direct_costs_pyg, p["pyg_per_brl"])
        gross_margin = gross_profit_brl / rev_brl if rev_brl else 0
        ebitda_margin = ebitda_brl / rev_brl if rev_brl else 0
        net_margin = net_remitted_brl / rev_brl if rev_brl else 0

        rows.append(
            {
                "Año": y,
                "Ingresos BRL": rev_brl,
                "OPEX - Salarios BRL": brl_from_pyg(salary_annual_pyg, p["pyg_per_brl"]),
                "OPEX - Prestadores PJ BRL": brl_from_pyg(contractors_annual_pyg, p["pyg_per_brl"]),
                "OPEX - Aguinaldo BRL": brl_from_pyg(aguinaldo_pyg, p["pyg_per_brl"]),
                "OPEX - IPS patronal BRL": brl_from_pyg(ips_pyg, p["pyg_per_brl"]),
                "OPEX - Alquiler oficina BRL": brl_from_pyg(rent_base_pyg, p["pyg_per_brl"]),
                "OPEX - Contabilidad BRL": brl_from_pyg(accounting_pyg, p["pyg_per_brl"]),
                "OPEX - Asesorías BRL": brl_from_pyg(advisory_pyg, p["pyg_per_brl"]),
                "OPEX - Regulatorios BRL": brl_from_pyg(regulatory_pyg, p["pyg_per_brl"]),
                "OPEX - Electricidad/servicios BRL": brl_from_pyg(utilities_pyg, p["pyg_per_brl"]),
                "OPEX - Internet BRL": brl_from_pyg(internet_pyg, p["pyg_per_brl"]),
                "OPEX - Telefonía BRL": brl_from_pyg(phone_pyg, p["pyg_per_brl"]),
                "OPEX - Seguros BRL": brl_from_pyg(insurance_pyg, p["pyg_per_brl"]),
                "OPEX - Software BRL": brl_from_pyg(software_pyg, p["pyg_per_brl"]),
                "OPEX - Librería/papelería BRL": brl_from_pyg(supplies_total_pyg, p["pyg_per_brl"]),
                "CAPEX - Constitución EAS BRL": brl_from_usd(p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"]) if y == 1 else 0,
                "CAPEX - Certificado facturación electrónica BRL": brl_from_pyg(p["invoice_cert_pyg"], p["pyg_per_brl"]) if y == 1 else 0,
                "CAPEX - Sello societario BRL": brl_from_pyg(p["seal_pyg"], p["pyg_per_brl"]) if y == 1 else 0,
                "CAPEX - Mobiliario/oficina inicial BRL": brl_from_pyg(p["office_setup_pyg"], p["pyg_per_brl"]) if y == 1 else 0,
                "CAPEX - Equipos informáticos BRL": brl_from_pyg(p["computer_count"] * p["computer_unit_pyg"], p["pyg_per_brl"]) if y == 1 else 0,
                "IVA crédito - General BRL": brl_from_pyg(iva_credit_general_pyg, p["pyg_per_brl"]),
                "IVA crédito - Alquiler BRL": brl_from_pyg(iva_credit_rent_pyg, p["pyg_per_brl"]),
                "Servicios personales BRL": brl_from_pyg(personal_pyg, p["pyg_per_brl"]),
                "Servicios no personales BRL": brl_from_pyg(non_personal_pyg, p["pyg_per_brl"]),
                "Bienes consumo e insumos BRL": brl_from_pyg(supplies_total_pyg, p["pyg_per_brl"]),
                "OPEX BRL": opex_brl,
                "CAPEX BRL": capex_brl,
                "IVA crédito fiscal BRL": brl_from_pyg(iva_credit_pyg, p["pyg_per_brl"]),
                "Resultado bruto BRL": gross_profit_brl,
                "Margen bruto": gross_margin,
                "EBITDA BRL": ebitda_brl,
                "Margen EBITDA": ebitda_margin,
                "Resultado operativo antes de impuestos BRL": operating_profit_before_tax_brl,
                "IRE BRL": ire_brl,
                "Resultado después de IRE BRL": profit_after_ire_brl,
                "IDU BRL": idu_brl,
                "Resultado neto remitible BRL": net_remitted_brl,
                "Margen neto": net_margin,
                "Flujo de caja neto BRL": cash_flow_brl,
                "Egresos de caja BRL": total_cash_outflows_brl,
                "Impuestos y contribuciones BRL": ire_brl + idu_brl,
            }
        )

    df = pd.DataFrame(rows)
    df["Flujo acumulado BRL"] = df["Flujo de caja neto BRL"].cumsum()
    return df


def input_number(label, id_, value, step=1, min_=0, suffix=None):
    return dbc.Col(
        [
            dbc.Label(label, className="small fw-semibold"),
            dbc.InputGroup(
                [
                    dbc.Input(id=id_, type="number", value=value, step=step, min=min_),
                    dbc.InputGroupText(suffix) if suffix else html.Span(),
                ]
            ),
        ],
        md=3,
        sm=6,
        xs=12,
        className="mb-3",
    )


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

controls = dbc.Card(
    [
        dbc.CardHeader(html.H5("Calculadora de supuestos", className="m-0")),
        dbc.CardBody(
            [
                html.H6("Moneda de presentación"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Mostrar resultados en", className="small fw-semibold"),
                                dbc.RadioItems(
                                    id="display_currency",
                                    options=[
                                        {"label": "Reales brasileños (BRL)", "value": "BRL"},
                                        {"label": "Guaraníes (PYG)", "value": "PYG"},
                                    ],
                                    value="BRL",
                                    inline=True,
                                    inputClassName="me-1",
                                    labelClassName="me-3",
                                ),
                            ],
                            md=12,
                            className="mb-3",
                        )
                    ]
                ),
                html.Hr(),
                html.H6("Horizonte temporal"),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Años de proyección", className="small fw-semibold"),
                                dcc.Slider(
                                    id="years",
                                    min=1,
                                    max=20,
                                    step=1,
                                    value=DEFAULTS["years"],
                                    marks={i: str(i) for i in range(1, 21)},
                                    tooltip={"placement": "bottom", "always_visible": True},
                                ),
                            ],
                            md=12,
                            className="mb-4",
                        )
                    ]
                ),
                html.Hr(),
                html.H6("Ingresos y tipo de cambio"),
                dbc.Row(
                    [
                        input_number("Facturación anual inicial", "annual_revenue_brl", DEFAULTS["annual_revenue_brl"], 100000, 0, "BRL"),
                        input_number("Crecimiento anual ingresos", "revenue_growth", DEFAULTS["revenue_growth"] * 100, 0.5, -100, "%"),
                        input_number("PYG por BRL", "pyg_per_brl", DEFAULTS["pyg_per_brl"], 10, 1),
                        input_number("PYG por USD", "pyg_per_usd", DEFAULTS["pyg_per_usd"], 10, 1),
                    ]
                ),
                html.Hr(),
                html.H6("Servicios personales"),
                dbc.Row(
                    [
                        input_number("Funcionarios", "employee_count", DEFAULTS["employee_count"], 1, 0),
                        input_number("Salario mensual por funcionario", "monthly_salary_pyg", DEFAULTS["monthly_salary_pyg"], 100000, 0, "PYG"),
                        input_number("Prestadores PJ", "contractor_count", DEFAULTS["contractor_count"], 1, 0),
                        input_number("Fee mensual PJ", "monthly_contractor_fee_pyg", DEFAULTS["monthly_contractor_fee_pyg"], 100000, 0, "PYG"),
                        input_number("IPS patronal", "ips_employer", DEFAULTS["ips_employer"] * 100, 0.1, 0, "%"),
                    ]
                ),
                dbc.Checklist(
                    options=[{"label": "Incluir aguinaldo e IPS para funcionarios en relación de dependencia", "value": 1}],
                    value=[1],
                    id="use_payroll",
                    switch=True,
                    className="mb-2",
                ),
                html.Hr(),
                html.H6("Servicios no personales y costos operativos"),
                dbc.Row(
                    [
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
                    ]
                ),
                html.Hr(),
                html.H6("CAPEX / inversión inicial"),
                dbc.Row(
                    [
                        input_number("Constitución EAS", "incorporation_usd", DEFAULTS["incorporation_usd"], 10, 0, "USD"),
                        input_number("Certificado facturación electrónica", "invoice_cert_pyg", DEFAULTS["invoice_cert_pyg"], 10000, 0, "PYG"),
                        input_number("Sello societario", "seal_pyg", DEFAULTS["seal_pyg"], 10000, 0, "PYG"),
                        input_number("Mobiliario/oficina inicial", "office_setup_pyg", DEFAULTS["office_setup_pyg"], 100000, 0, "PYG"),
                        input_number("Cantidad computadoras", "computer_count", DEFAULTS["computer_count"], 1, 0),
                        input_number("Costo unitario computadora", "computer_unit_pyg", DEFAULTS["computer_unit_pyg"], 100000, 0, "PYG"),
                    ]
                ),
                html.Hr(),
                html.H6("Impuestos Paraguay e IVA crédito"),
                dbc.Row(
                    [
                        input_number("IRE", "ire_rate", DEFAULTS["ire_rate"] * 100, 0.1, 0, "%"),
                        input_number("IDU no residente", "idu_nonresident_rate", DEFAULTS["idu_nonresident_rate"] * 100, 0.1, 0, "%"),
                        input_number("% utilidad distribuida", "dividend_distribution_rate", DEFAULTS["dividend_distribution_rate"] * 100, 1, 0, "%"),
                        input_number("IVA crédito gastos generales", "expense_vat_general", DEFAULTS["expense_vat_general"] * 100, 0.1, 0, "%"),
                        input_number("IVA crédito alquiler", "rent_vat", DEFAULTS["rent_vat"] * 100, 0.1, 0, "%"),
                    ]
                ),
                html.Hr(),
                html.H6("Actualización temporal de costos"),
                dbc.Row(
                    [
                        input_number("Inflación anual costos Paraguay", "inflation_py", DEFAULTS["inflation_py"] * 100, 0.5, 0, "%"),
                    ]
                ),
            ]
        ),
    ],
    className="shadow-sm mb-4",
)

explanatory_notes = dbc.Accordion(
    [
        dbc.AccordionItem(
            [
                html.P("OPEX son los gastos operativos necesarios para mantener la operación funcionando año a año. En este modelo incluye servicios personales, servicios no personales y bienes de consumo e insumos."),
                html.P("CAPEX es inversión de capital. En este modelo corresponde principalmente a apertura, mobiliario, equipos informáticos y elementos iniciales. Se muestra como salida de caja en el año 1, pero no se descuenta como gasto operativo para calcular EBITDA ni base de IRE."),
                html.P("Servicios personales incluye salarios, prestadores PJ, aguinaldo e IPS patronal cuando corresponde. Los salarios no generan IVA crédito; los prestadores PJ sí generan IVA crédito si facturan servicios gravados."),
                html.P("Servicios no personales incluye alquiler, contabilidad, asesorías, costos regulatorios, electricidad, internet, telefonía, seguros y software. Son gastos de terceros necesarios para operar."),
                html.P("Como se modela una exportación de servicios, la herramienta no calcula IVA débito sobre ingresos. En cambio, estima el IVA crédito generado por compras y servicios gravados. Ese IVA crédito se muestra separado y no se trata como gasto operativo."),
            ],
            title="Qué significan OPEX, CAPEX, servicios personales, servicios no personales e IVA crédito",
        ),
        dbc.AccordionItem(
            [
                html.P("Margen bruto: resultado después de descontar costos directos estimados, principalmente servicios personales y software, sobre ingresos."),
                html.P("EBITDA: ingresos menos OPEX. Es una aproximación del resultado operativo antes de impuestos, intereses, depreciaciones y amortizaciones."),
                html.P("Margen neto: resultado neto remitible dividido por ingresos."),
                html.P("Flujo acumulado: suma anual del flujo de caja neto. El flujo de caja neto considera resultado neto remitible menos CAPEX."),
            ],
            title="Cómo leer márgenes, EBITDA y flujo acumulado",
        ),
    ],
    start_collapsed=True,
    className="mb-4",
)

app.layout = html.Div(
    [
        html.Header(
            dbc.Container(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    html.H1(
                                        APP_TITLE,
                                        className="m-0",
                                        style={
                                            "fontFamily": "Avenir, Arial, sans-serif",
                                            "fontWeight": "700",
                                            "fontSize": "2rem",
                                            "color": "#333",
                                        },
                                    ),
                                    html.P(
                                        "Modelo editable para proyectar ingresos, egresos, impuestos, EBITDA, márgenes y flujo de caja de la operación paraguaya.",
                                        className="text-muted mb-0",
                                    ),
                                ],
                                md=10,
                            )
                        ],
                        justify="center",
                        className="py-4",
                    )
                ]
            ),
            style={"backgroundColor": "white", "borderBottom": "1px solid #eee"},
        ),
        dbc.Container(
            [
                dbc.Alert(
                    "Nota: este modelo es una herramienta de análisis financiero. Validar el encuadre fiscal final con contador/abogado tributario, especialmente IVA crédito de exportadores, precios de transferencia y retenciones aplicables.",
                    color="warning",
                    className="mt-3",
                ),
                controls,
                explanatory_notes,
                dbc.Row(id="kpi_cards", className="g-3 mb-4"),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(id="evolution_chart"), md=8),
                        dbc.Col(dcc.Graph(id="margin_chart"), md=4),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(id="cost_breakdown_chart"), md=6),
                        dbc.Col(dcc.Graph(id="tax_chart"), md=6),
                    ]
                ),
                dbc.Row(
                    [
                        dbc.Col(dcc.Graph(id="cashflow_chart"), md=12),
                    ]
                ),
                html.H4("Cuadro general por grandes rubros", className="mt-4"),
                html.P(
                    "Este cuadro resume la evolución anual de ingresos, OPEX, CAPEX, impuestos, resultado neto y flujo acumulado.",
                    className="text-muted",
                ),
                dash_table.DataTable(
                    id="summary_table",
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
                html.H4("Cuadro detallado por cuenta", className="mt-4"),
                html.P(
                    "Este cuadro abre OPEX y CAPEX por cuenta específica para ver cómo evoluciona cada componente año a año.",
                    className="text-muted",
                ),
                dash_table.DataTable(
                    id="detail_table",
                    page_size=25,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px"},
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                    style_data_conditional=[
                        {"if": {"filter_query": "{Rubro nivel 1} = OPEX"}, "backgroundColor": "#fbfcff"},
                        {"if": {"filter_query": "{Rubro nivel 1} = CAPEX"}, "backgroundColor": "#fffaf0"},
                    ],
                ),
                html.H4("Tabla completa del modelo", className="mt-4"),
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
            ],
            fluid=True,
        ),
    ],
    style={"backgroundColor": "#f7f8fa", "minHeight": "100vh"},
)


def collect_params(*values):
    keys = [
        "years",
        "annual_revenue_brl",
        "revenue_growth",
        "pyg_per_brl",
        "pyg_per_usd",
        "employee_count",
        "monthly_salary_pyg",
        "contractor_count",
        "monthly_contractor_fee_pyg",
        "ips_employer",
        "use_payroll",
        "monthly_office_rent_pyg",
        "accounting_monthly_pyg",
        "advisory_annual_pyg",
        "regulatory_annual_pyg",
        "utilities_monthly_pyg",
        "internet_monthly_pyg",
        "phone_monthly_pyg",
        "insurance_annual_pyg",
        "supplies_monthly_pyg",
        "software_monthly_pyg",
        "incorporation_usd",
        "invoice_cert_pyg",
        "seal_pyg",
        "office_setup_pyg",
        "computer_count",
        "computer_unit_pyg",
        "ire_rate",
        "idu_nonresident_rate",
        "dividend_distribution_rate",
        "expense_vat_general",
        "rent_vat",
        "inflation_py",
    ]
    p = DEFAULTS.copy()
    for k, v in zip(keys, values):
        if k == "use_payroll":
            p[k] = bool(v)
        elif k in [
            "revenue_growth",
            "ips_employer",
            "ire_rate",
            "idu_nonresident_rate",
            "dividend_distribution_rate",
            "expense_vat_general",
            "rent_vat",
            "inflation_py",
        ]:
            p[k] = (v or 0) / 100
        elif k in ["years", "employee_count", "contractor_count", "computer_count"]:
            p[k] = int(v or 0)
        else:
            p[k] = v or 0
    p["years"] = max(1, int(p["years"]))
    p["aguinaldo_rate"] = 1 / 12
    return p


model_inputs = [
    Input("years", "value"),
    Input("annual_revenue_brl", "value"),
    Input("revenue_growth", "value"),
    Input("pyg_per_brl", "value"),
    Input("pyg_per_usd", "value"),
    Input("employee_count", "value"),
    Input("monthly_salary_pyg", "value"),
    Input("contractor_count", "value"),
    Input("monthly_contractor_fee_pyg", "value"),
    Input("ips_employer", "value"),
    Input("use_payroll", "value"),
    Input("monthly_office_rent_pyg", "value"),
    Input("accounting_monthly_pyg", "value"),
    Input("advisory_annual_pyg", "value"),
    Input("regulatory_annual_pyg", "value"),
    Input("utilities_monthly_pyg", "value"),
    Input("internet_monthly_pyg", "value"),
    Input("phone_monthly_pyg", "value"),
    Input("insurance_annual_pyg", "value"),
    Input("supplies_monthly_pyg", "value"),
    Input("software_monthly_pyg", "value"),
    Input("incorporation_usd", "value"),
    Input("invoice_cert_pyg", "value"),
    Input("seal_pyg", "value"),
    Input("office_setup_pyg", "value"),
    Input("computer_count", "value"),
    Input("computer_unit_pyg", "value"),
    Input("ire_rate", "value"),
    Input("idu_nonresident_rate", "value"),
    Input("dividend_distribution_rate", "value"),
    Input("expense_vat_general", "value"),
    Input("rent_vat", "value"),
    Input("inflation_py", "value"),
]


def presentation_df(df, currency, pyg_per_brl):
    out = df.copy()
    monetary_cols = [col for col in out.columns if col.endswith("BRL")]
    for col in monetary_cols:
        out[col] = out[col].apply(lambda x: convert_from_brl(x, currency, pyg_per_brl))
        out.rename(columns={col: col.replace(" BRL", f" {currency}")}, inplace=True)
    return out


def format_table_numbers(table_df):
    out = table_df.copy()
    for col in out.columns:
        if col in ["Rubro nivel 1", "Rubro nivel 2", "Cuenta"]:
            continue
        if col != "Año":
            if "Margen" in col:
                out[col] = (out[col] * 100).round(2).astype(str) + "%"
            else:
                out[col] = out[col].round(0).astype(int)
    return out


def build_summary_table(display, currency):
    cols = [
        "Año",
        f"Ingresos {currency}",
        f"Servicios personales {currency}",
        f"Servicios no personales {currency}",
        f"Bienes consumo e insumos {currency}",
        f"OPEX {currency}",
        f"CAPEX {currency}",
        f"IRE {currency}",
        f"IDU {currency}",
        f"IVA crédito fiscal {currency}",
        f"Resultado neto remitible {currency}",
        f"Flujo de caja neto {currency}",
        f"Flujo acumulado {currency}",
        "Margen bruto",
        "Margen EBITDA",
        "Margen neto",
    ]
    return display[[c for c in cols if c in display.columns]].copy()


def build_detail_table(display, currency):
    mapping = [
        ("OPEX", "Servicios personales", "Salarios", f"OPEX - Salarios {currency}"),
        ("OPEX", "Servicios personales", "Prestadores PJ", f"OPEX - Prestadores PJ {currency}"),
        ("OPEX", "Servicios personales", "Aguinaldo", f"OPEX - Aguinaldo {currency}"),
        ("OPEX", "Servicios personales", "IPS patronal", f"OPEX - IPS patronal {currency}"),
        ("OPEX", "Servicios no personales", "Alquiler oficina", f"OPEX - Alquiler oficina {currency}"),
        ("OPEX", "Servicios no personales", "Contabilidad", f"OPEX - Contabilidad {currency}"),
        ("OPEX", "Servicios no personales", "Asesorías", f"OPEX - Asesorías {currency}"),
        ("OPEX", "Servicios no personales", "Regulatorios", f"OPEX - Regulatorios {currency}"),
        ("OPEX", "Servicios no personales", "Electricidad/servicios", f"OPEX - Electricidad/servicios {currency}"),
        ("OPEX", "Servicios no personales", "Internet", f"OPEX - Internet {currency}"),
        ("OPEX", "Servicios no personales", "Telefonía", f"OPEX - Telefonía {currency}"),
        ("OPEX", "Servicios no personales", "Seguros", f"OPEX - Seguros {currency}"),
        ("OPEX", "Servicios no personales", "Software", f"OPEX - Software {currency}"),
        ("OPEX", "Bienes de consumo e insumos", "Librería/papelería", f"OPEX - Librería/papelería {currency}"),
        ("CAPEX", "Apertura e inversión inicial", "Constitución EAS", f"CAPEX - Constitución EAS {currency}"),
        ("CAPEX", "Apertura e inversión inicial", "Certificado facturación electrónica", f"CAPEX - Certificado facturación electrónica {currency}"),
        ("CAPEX", "Apertura e inversión inicial", "Sello societario", f"CAPEX - Sello societario {currency}"),
        ("CAPEX", "Apertura e inversión inicial", "Mobiliario/oficina inicial", f"CAPEX - Mobiliario/oficina inicial {currency}"),
        ("CAPEX", "Apertura e inversión inicial", "Equipos informáticos", f"CAPEX - Equipos informáticos {currency}"),
        ("Fiscal", "IVA crédito", "IVA crédito general", f"IVA crédito - General {currency}"),
        ("Fiscal", "IVA crédito", "IVA crédito alquiler", f"IVA crédito - Alquiler {currency}"),
        ("Fiscal", "Impuestos", "IRE", f"IRE {currency}"),
        ("Fiscal", "Impuestos", "IDU", f"IDU {currency}"),
    ]
    rows = []
    for rubro1, rubro2, cuenta, col in mapping:
        if col not in display.columns:
            continue
        row = {"Rubro nivel 1": rubro1, "Rubro nivel 2": rubro2, "Cuenta": cuenta}
        for _, r in display.iterrows():
            row[f"Año {int(r['Año'])}"] = r[col]
        rows.append(row)
    return pd.DataFrame(rows)


@app.callback(
    Output("kpi_cards", "children"),
    Output("evolution_chart", "figure"),
    Output("margin_chart", "figure"),
    Output("cost_breakdown_chart", "figure"),
    Output("tax_chart", "figure"),
    Output("cashflow_chart", "figure"),
    Output("summary_table", "data"),
    Output("summary_table", "columns"),
    Output("detail_table", "data"),
    Output("detail_table", "columns"),
    Output("model_table", "data"),
    Output("model_table", "columns"),
    Input("display_currency", "value"),
    *model_inputs,
)
def update_dashboard(display_currency, *values):
    p = collect_params(*values)
    df = compute_model(p)
    pyg_per_brl = p["pyg_per_brl"]
    prefix = currency_label(display_currency)

    total_revenue = df["Ingresos BRL"].sum()
    total_opex = df["OPEX BRL"].sum()
    total_ebitda = df["EBITDA BRL"].sum()
    total_net = df["Resultado neto remitible BRL"].sum()
    final_accumulated_flow = df["Flujo acumulado BRL"].iloc[-1]
    avg_gross_margin = df["Margen bruto"].mean()
    avg_net_margin = df["Margen neto"].mean()
    years_label = f"{p['years']} año" if p["years"] == 1 else f"{p['years']} años"

    def kpi(title, value, subtitle=""):
        return dbc.Col(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(title, className="text-muted small"),
                        html.H3(value, className="mb-1"),
                        html.Div(subtitle, className="small text-muted"),
                    ]
                ),
                className="shadow-sm border-0",
            ),
            md=3,
            sm=6,
        )

    cards = [
        kpi("Ingresos acumulados", fmt_money_dynamic(total_revenue, display_currency, pyg_per_brl), years_label),
        kpi("EBITDA acumulado", fmt_money_dynamic(total_ebitda, display_currency, pyg_per_brl), "Ingresos - OPEX"),
        kpi("Resultado neto acumulado", fmt_money_dynamic(total_net, display_currency, pyg_per_brl), "Luego de IRE e IDU"),
        kpi("Flujo acumulado", fmt_money_dynamic(final_accumulated_flow, display_currency, pyg_per_brl), "Resultado neto - CAPEX"),
        kpi("Margen bruto promedio", f"{avg_gross_margin * 100:.1f}%", years_label),
        kpi("Margen neto promedio", f"{avg_net_margin * 100:.1f}%", years_label),
        kpi("OPEX acumulado", fmt_money_dynamic(total_opex, display_currency, pyg_per_brl), "Gastos operativos"),
        kpi("IVA crédito acumulado", fmt_money_dynamic(df["IVA crédito fiscal BRL"].sum(), display_currency, pyg_per_brl), "No incluye IVA débito"),
    ]

    display = presentation_df(df, display_currency, pyg_per_brl)
    money_suffix = display_currency

    evolution_cols = [f"Ingresos {money_suffix}", f"OPEX {money_suffix}", f"EBITDA {money_suffix}", f"Resultado neto remitible {money_suffix}"]
    evolution_long = display.melt(
        id_vars="Año",
        value_vars=evolution_cols,
        var_name="Concepto",
        value_name=display_currency,
    )
    fig_evolution = px.line(
        evolution_long,
        x="Año",
        y=display_currency,
        color="Concepto",
        markers=True,
        template="plotly_white",
        title="Evolución temporal de ingresos, OPEX, EBITDA y resultado neto",
    )
    fig_evolution.update_layout(legend_title_text="", yaxis_tickprefix=f"{prefix} ", title_font=dict(size=18))

    margin_long = df.melt(
        id_vars="Año",
        value_vars=["Margen bruto", "Margen EBITDA", "Margen neto"],
        var_name="Indicador",
        value_name="Margen",
    )
    fig_margin = px.line(
        margin_long,
        x="Año",
        y="Margen",
        color="Indicador",
        markers=True,
        template="plotly_white",
        title="Evolución de márgenes",
    )
    fig_margin.update_layout(legend_title_text="", yaxis_tickformat=".1%", title_font=dict(size=18))

    cost_cols = [
        f"Servicios personales {money_suffix}",
        f"Servicios no personales {money_suffix}",
        f"Bienes consumo e insumos {money_suffix}",
        f"CAPEX {money_suffix}",
    ]
    cost_long = display.melt(id_vars="Año", value_vars=cost_cols, var_name="Rubro", value_name=display_currency)
    fig_cost = px.area(
        cost_long,
        x="Año",
        y=display_currency,
        color="Rubro",
        template="plotly_white",
        title="Estructura de egresos e inversión",
    )
    fig_cost.update_layout(legend_title_text="", yaxis_tickprefix=f"{prefix} ", title_font=dict(size=18))

    tax_long = display.melt(
        id_vars="Año",
        value_vars=[f"IRE {money_suffix}", f"IDU {money_suffix}", f"IVA crédito fiscal {money_suffix}"],
        var_name="Concepto fiscal",
        value_name=display_currency,
    )
    fig_tax = px.bar(
        tax_long,
        x="Año",
        y=display_currency,
        color="Concepto fiscal",
        barmode="group",
        template="plotly_white",
        title="IRE, IDU e IVA crédito fiscal estimado",
    )
    fig_tax.update_layout(legend_title_text="", yaxis_tickprefix=f"{prefix} ", title_font=dict(size=18))

    cash_cols = [f"Flujo de caja neto {money_suffix}", f"Flujo acumulado {money_suffix}"]
    cash_long = display.melt(id_vars="Año", value_vars=cash_cols, var_name="Concepto", value_name=display_currency)
    fig_cash = px.line(
        cash_long,
        x="Año",
        y=display_currency,
        color="Concepto",
        markers=True,
        template="plotly_white",
        title="Flujo de caja neto y flujo acumulado",
    )
    fig_cash.update_layout(legend_title_text="", yaxis_tickprefix=f"{prefix} ", title_font=dict(size=18))

    summary_df = format_table_numbers(build_summary_table(display, display_currency))
    summary_columns = [{"name": c, "id": c} for c in summary_df.columns]

    detail_df = format_table_numbers(build_detail_table(display, display_currency))
    detail_columns = [{"name": c, "id": c} for c in detail_df.columns]

    table_df = format_table_numbers(display.copy())
    columns = [{"name": c, "id": c} for c in table_df.columns]
    return (
        cards,
        fig_evolution,
        fig_margin,
        fig_cost,
        fig_tax,
        fig_cash,
        summary_df.to_dict("records"),
        summary_columns,
        detail_df.to_dict("records"),
        detail_columns,
        table_df.to_dict("records"),
        columns,
    )


@app.callback(
    Output("download_model", "data"),
    Input("download_btn", "n_clicks"),
    State("display_currency", "value"),
    *[State(i.component_id, i.component_property) for i in model_inputs],
    prevent_initial_call=True,
)
def download_csv(n_clicks, display_currency, *values):
    p = collect_params(*values)
    df = compute_model(p)
    out = presentation_df(df, display_currency, p["pyg_per_brl"])
    return dcc.send_data_frame(out.to_csv, f"modelo_operacion_paraguay_{display_currency.lower()}.csv", index=False)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
