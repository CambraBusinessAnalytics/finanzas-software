import os
import pandas as pd
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table

# ============================================================
# DASHBOARD FINANCIERO: OPERACIÓN PARAGUAY
# Horizonte editable
# Moneda de presentación: BRL / PYG
#
# Corrección CAPEX / IRE:
# - El CAPEX se muestra como salida de caja.
# - Los gastos de apertura deducibles reducen la base del IRE en el año 1.
# - Los activos fijos reducen la base del IRE vía depreciación fiscal.
# ============================================================

APP_TITLE = "Análisis financiero: operación en Paraguay"

DEFAULTS = {
    "years": 10,
    "display_currency": "BRL",

    # Ingresos y tipo de cambio
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
    # Estos conceptos se separan entre:
    # 1) Gastos de apertura deducibles en año 1.
    # 2) Activos fijos depreciables.
    "incorporation_usd": 400,
    "invoice_cert_pyg": 480_000,
    "seal_pyg": 130_000,
    "office_setup_pyg": 10_000_000,
    "computer_count": 8,
    "computer_unit_pyg": 3_000_000,

    # Tratamiento fiscal CAPEX
    "deduct_startup_expenses_year1": True,
    "depreciate_fixed_assets": True,
    "office_setup_life_years": 5,
    "computer_life_years": 4,

    # Impuestos Paraguay
    "ire_rate": 0.10,
    "idu_nonresident_rate": 0.15,
    "dividend_distribution_rate": 1.00,
    "expense_vat_general": 0.10,
    "rent_vat": 0.10,
    "calculate_vat_credit": True,
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def brl_from_pyg(value_pyg, pyg_per_brl):
    if pyg_per_brl <= 0:
        return 0
    return value_pyg / pyg_per_brl


def pyg_from_brl(value_brl, pyg_per_brl):
    return value_brl * pyg_per_brl


def brl_from_usd(value_usd, pyg_per_usd, pyg_per_brl):
    return brl_from_pyg(value_usd * pyg_per_usd, pyg_per_brl)


def display_value(value_brl, p):
    """Convierte un valor base BRL a la moneda elegida para presentación."""
    if p["display_currency"] == "PYG":
        return pyg_from_brl(value_brl, p["pyg_per_brl"])
    return value_brl


def money_prefix(p):
    return "Gs. " if p["display_currency"] == "PYG" else "R$ "


def fmt_money(x, p=None):
    prefix = money_prefix(p) if p else "R$ "
    return f"{prefix}{x:,.0f}".replace(",", ".")


def pct(x):
    return f"{x * 100:.1f}%"


def safe_div(a, b):
    return a / b if b else 0


# ============================================================
# MODELO FINANCIERO
# ============================================================

def compute_model(p):
    years = max(1, int(p["years"]))
    rows = []
    detail_rows = []

    # Gastos de apertura: en caja son CAPEX/salida inicial.
    # Fiscalmente pueden tratarse como deducibles en año 1 según criterio validado.
    incorporation_brl = brl_from_usd(p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"])
    invoice_cert_brl = brl_from_pyg(p["invoice_cert_pyg"], p["pyg_per_brl"])
    seal_brl = brl_from_pyg(p["seal_pyg"], p["pyg_per_brl"])

    startup_expenses_brl = incorporation_brl + invoice_cert_brl + seal_brl

    # Activos fijos: salida de caja en año 1; deducción fiscal vía depreciación.
    office_setup_brl = brl_from_pyg(p["office_setup_pyg"], p["pyg_per_brl"])
    computer_assets_brl = brl_from_pyg(p["computer_count"] * p["computer_unit_pyg"], p["pyg_per_brl"])
    fixed_assets_brl = office_setup_brl + computer_assets_brl

    total_initial_capex_cash_brl = startup_expenses_brl + fixed_assets_brl

    # Depreciación lineal simple.
    office_dep_annual_brl = safe_div(office_setup_brl, max(1, int(p["office_setup_life_years"])))
    computer_dep_annual_brl = safe_div(computer_assets_brl, max(1, int(p["computer_life_years"])))

    for y in range(1, years + 1):
        rev_brl = p["annual_revenue_brl"] * ((1 + p["revenue_growth"]) ** (y - 1))
        py_infl = (1 + p["inflation_py"]) ** (y - 1)

        # ------------------------------------------------------------
        # SERVICIOS PERSONALES
        # ------------------------------------------------------------
        salary_annual_pyg = p["employee_count"] * p["monthly_salary_pyg"] * 12 * py_infl
        contractors_annual_pyg = p["contractor_count"] * p["monthly_contractor_fee_pyg"] * 12 * py_infl

        if p["use_payroll"]:
            aguinaldo_pyg = salary_annual_pyg * p["aguinaldo_rate"]
            ips_pyg = salary_annual_pyg * p["ips_employer"]
        else:
            aguinaldo_pyg = 0
            ips_pyg = 0

        salary_brl = brl_from_pyg(salary_annual_pyg, p["pyg_per_brl"])
        contractors_brl = brl_from_pyg(contractors_annual_pyg, p["pyg_per_brl"])
        aguinaldo_brl = brl_from_pyg(aguinaldo_pyg, p["pyg_per_brl"])
        ips_brl = brl_from_pyg(ips_pyg, p["pyg_per_brl"])
        personal_brl = salary_brl + contractors_brl + aguinaldo_brl + ips_brl

        # ------------------------------------------------------------
        # SERVICIOS NO PERSONALES Y GASTOS OPERATIVOS
        # ------------------------------------------------------------
        rent_brl = brl_from_pyg(p["monthly_office_rent_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        accounting_brl = brl_from_pyg(p["accounting_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        advisory_brl = brl_from_pyg(p["advisory_annual_pyg"] * py_infl, p["pyg_per_brl"])
        regulatory_brl = brl_from_pyg(p["regulatory_annual_pyg"] * py_infl, p["pyg_per_brl"])
        utilities_brl = brl_from_pyg(p["utilities_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        internet_brl = brl_from_pyg(p["internet_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        phone_brl = brl_from_pyg(p["phone_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        insurance_brl = brl_from_pyg(p["insurance_annual_pyg"] * py_infl, p["pyg_per_brl"])
        software_brl = brl_from_pyg(p["software_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])

        non_personal_brl = (
            rent_brl + accounting_brl + advisory_brl + regulatory_brl +
            utilities_brl + internet_brl + phone_brl + insurance_brl + software_brl
        )

        # ------------------------------------------------------------
        # BIENES DE CONSUMO E INSUMOS
        # ------------------------------------------------------------
        supplies_brl = brl_from_pyg(p["supplies_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])

        # ------------------------------------------------------------
        # IVA CRÉDITO FISCAL
        # Exportación de servicios: no se modela IVA débito sobre ingresos.
        # Se calcula IVA crédito por compras/servicios gravados.
        # Salarios, aguinaldo e IPS no generan IVA crédito.
        # Prestadores PJ, servicios no personales y bienes de consumo sí.
        # ------------------------------------------------------------
        vat_credit_general_base_brl = (
            contractors_brl + accounting_brl + advisory_brl + regulatory_brl +
            utilities_brl + internet_brl + phone_brl + insurance_brl +
            software_brl + supplies_brl
        )
        vat_credit_general_brl = vat_credit_general_base_brl * p["expense_vat_general"] if p["calculate_vat_credit"] else 0
        vat_credit_rent_brl = rent_brl * p["rent_vat"] if p["calculate_vat_credit"] else 0
        vat_credit_brl = vat_credit_general_brl + vat_credit_rent_brl

        # ------------------------------------------------------------
        # OPEX, EBITDA, RESULTADO FISCAL
        # ------------------------------------------------------------
        opex_brl = personal_brl + non_personal_brl + supplies_brl
        gross_profit_brl = rev_brl - personal_brl
        ebitda_brl = rev_brl - opex_brl

        # Fiscalmente:
        # - gastos de apertura deducibles en año 1, si está activado.
        # - activos fijos vía depreciación anual, si está activado.
        startup_deductible_brl = startup_expenses_brl if (y == 1 and p["deduct_startup_expenses_year1"]) else 0

        office_depreciation_brl = (
            office_dep_annual_brl
            if p["depreciate_fixed_assets"] and y <= int(p["office_setup_life_years"])
            else 0
        )
        computer_depreciation_brl = (
            computer_dep_annual_brl
            if p["depreciate_fixed_assets"] and y <= int(p["computer_life_years"])
            else 0
        )
        depreciation_brl = office_depreciation_brl + computer_depreciation_brl

        taxable_income_ire_brl = ebitda_brl - startup_deductible_brl - depreciation_brl
        ire_brl = max(0, taxable_income_ire_brl * p["ire_rate"])

        profit_after_ire_brl = ebitda_brl - ire_brl
        idu_brl = max(
            0,
            profit_after_ire_brl * p["dividend_distribution_rate"] * p["idu_nonresident_rate"],
        )
        net_remitted_brl = profit_after_ire_brl - idu_brl

        # CAPEX como salida de caja: se desembolsa en año 1.
        capex_cash_brl = total_initial_capex_cash_brl if y == 1 else 0
        cash_flow_brl = net_remitted_brl - capex_cash_brl

        rows.append(
            {
                "Año": y,
                "Ingresos BRL": rev_brl,
                "Servicios personales BRL": personal_brl,
                "Servicios no personales BRL": non_personal_brl,
                "Bienes consumo e insumos BRL": supplies_brl,
                "OPEX BRL": opex_brl,
                "Margen bruto BRL": gross_profit_brl,
                "EBITDA BRL": ebitda_brl,
                "Gastos apertura deducibles IRE BRL": startup_deductible_brl,
                "Depreciación fiscal BRL": depreciation_brl,
                "Base IRE BRL": taxable_income_ire_brl,
                "IRE BRL": ire_brl,
                "Resultado después de IRE BRL": profit_after_ire_brl,
                "IDU BRL": idu_brl,
                "Resultado neto remitible BRL": net_remitted_brl,
                "CAPEX caja BRL": capex_cash_brl,
                "Flujo de caja neto BRL": cash_flow_brl,
                "IVA crédito fiscal BRL": vat_credit_brl,
                "IVA crédito general BRL": vat_credit_general_brl,
                "IVA crédito alquiler BRL": vat_credit_rent_brl,
                "Margen bruto": safe_div(gross_profit_brl, rev_brl),
                "Margen EBITDA": safe_div(ebitda_brl, rev_brl),
                "Margen neto": safe_div(net_remitted_brl, rev_brl),
            }
        )

        # Detalle por cuenta, base BRL.
        details_this_year = [
            ("Ingresos", "Facturación", "Ingresos por exportación de servicios", rev_brl),
            ("OPEX", "Servicios personales", "Salarios", salary_brl),
            ("OPEX", "Servicios personales", "Prestadores PJ", contractors_brl),
            ("OPEX", "Servicios personales", "Aguinaldo", aguinaldo_brl),
            ("OPEX", "Servicios personales", "IPS patronal", ips_brl),
            ("OPEX", "Servicios no personales", "Alquiler oficina", rent_brl),
            ("OPEX", "Servicios no personales", "Contabilidad", accounting_brl),
            ("OPEX", "Servicios no personales", "Asesorías", advisory_brl),
            ("OPEX", "Servicios no personales", "Regulatorios", regulatory_brl),
            ("OPEX", "Servicios no personales", "Electricidad / servicios", utilities_brl),
            ("OPEX", "Servicios no personales", "Internet", internet_brl),
            ("OPEX", "Servicios no personales", "Telefonía", phone_brl),
            ("OPEX", "Servicios no personales", "Seguros", insurance_brl),
            ("OPEX", "Servicios no personales", "Software", software_brl),
            ("OPEX", "Bienes de consumo e insumos", "Librería / papelería", supplies_brl),
            ("Deducciones fiscales", "Gastos de apertura", "Constitución, certificados y sello deducibles", startup_deductible_brl),
            ("Deducciones fiscales", "Depreciación fiscal", "Depreciación mobiliario / oficina", office_depreciation_brl),
            ("Deducciones fiscales", "Depreciación fiscal", "Depreciación equipos informáticos", computer_depreciation_brl),
            ("Impuestos", "IRE", "IRE sobre base imponible", ire_brl),
            ("Impuestos", "IDU", "IDU sobre utilidad distribuida", idu_brl),
            ("IVA crédito fiscal", "IVA crédito", "IVA crédito general", vat_credit_general_brl),
            ("IVA crédito fiscal", "IVA crédito", "IVA crédito alquiler", vat_credit_rent_brl),
            ("CAPEX caja", "Gastos de apertura", "Constitución EAS", incorporation_brl if y == 1 else 0),
            ("CAPEX caja", "Gastos de apertura", "Certificado facturación electrónica", invoice_cert_brl if y == 1 else 0),
            ("CAPEX caja", "Gastos de apertura", "Sello societario", seal_brl if y == 1 else 0),
            ("CAPEX caja", "Activos fijos", "Mobiliario / oficina inicial", office_setup_brl if y == 1 else 0),
            ("CAPEX caja", "Activos fijos", "Equipos informáticos", computer_assets_brl if y == 1 else 0),
            ("Resultado", "Flujo", "Flujo de caja neto", cash_flow_brl),
        ]
        for rubro1, rubro2, cuenta, value in details_this_year:
            detail_rows.append(
                {
                    "Año": y,
                    "Rubro nivel 1": rubro1,
                    "Rubro nivel 2": rubro2,
                    "Cuenta": cuenta,
                    "Valor BRL": value,
                }
            )

    df = pd.DataFrame(rows)
    df["Flujo acumulado BRL"] = df["Flujo de caja neto BRL"].cumsum()
    detail_df = pd.DataFrame(detail_rows)

    # Agregar flujo acumulado al detalle.
    for _, row in df.iterrows():
        detail_df = pd.concat(
            [
                detail_df,
                pd.DataFrame(
                    [
                        {
                            "Año": int(row["Año"]),
                            "Rubro nivel 1": "Resultado",
                            "Rubro nivel 2": "Flujo",
                            "Cuenta": "Flujo acumulado",
                            "Valor BRL": row["Flujo acumulado BRL"],
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    return df, detail_df


def build_summary_table(df):
    rows = []
    mapping = [
        ("Ingresos", "Ingresos BRL"),
        ("Servicios personales", "Servicios personales BRL"),
        ("Servicios no personales", "Servicios no personales BRL"),
        ("Bienes de consumo e insumos", "Bienes consumo e insumos BRL"),
        ("OPEX total", "OPEX BRL"),
        ("Margen bruto", "Margen bruto BRL"),
        ("EBITDA", "EBITDA BRL"),
        ("Gastos apertura deducibles IRE", "Gastos apertura deducibles IRE BRL"),
        ("Depreciación fiscal", "Depreciación fiscal BRL"),
        ("Base IRE", "Base IRE BRL"),
        ("IRE", "IRE BRL"),
        ("IDU", "IDU BRL"),
        ("Resultado neto remitible", "Resultado neto remitible BRL"),
        ("CAPEX caja", "CAPEX caja BRL"),
        ("Flujo de caja neto", "Flujo de caja neto BRL"),
        ("Flujo acumulado", "Flujo acumulado BRL"),
        ("IVA crédito fiscal", "IVA crédito fiscal BRL"),
        ("Margen bruto %", "Margen bruto"),
        ("Margen EBITDA %", "Margen EBITDA"),
        ("Margen neto %", "Margen neto"),
    ]

    for label, col in mapping:
        row = {"Concepto": label}
        for _, r in df.iterrows():
            row[f"Año {int(r['Año'])}"] = r[col]
        rows.append(row)
    return pd.DataFrame(rows)


def build_detail_matrix(detail_df):
    matrix = detail_df.pivot_table(
        index=["Rubro nivel 1", "Rubro nivel 2", "Cuenta"],
        columns="Año",
        values="Valor BRL",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()
    matrix.columns = [
        f"Año {int(c)}" if isinstance(c, int) or str(c).isdigit() else c
        for c in matrix.columns
    ]
    return matrix


def convert_df_currency(df, p):
    out = df.copy()
    for col in out.columns:
        if col.endswith(" BRL"):
            new_col = col.replace(" BRL", f" {p['display_currency']}")
            out[new_col] = out[col].apply(lambda x: display_value(x, p))
            out = out.drop(columns=[col])
        elif col.startswith("Año "):
            # matrices de valores monetarios, no aplica para porcentajes si Concepto indica %
            out[col] = out[col].apply(lambda x: display_value(x, p) if isinstance(x, (int, float)) else x)
    return out


def format_table_df(df):
    out = df.copy()
    for col in out.columns:
        if col == "Año":
            continue
        if col in ["Margen bruto", "Margen EBITDA", "Margen neto"] or "Margen" in str(col) and "%" in str(out.get("Concepto", "")):
            pass

    for col in out.columns:
        if col == "Año":
            continue
        if pd.api.types.is_numeric_dtype(out[col]):
            # Columnas de margen en forma decimal
            if col in ["Margen bruto", "Margen EBITDA", "Margen neto"]:
                out[col] = (out[col] * 100).round(2).astype(str) + "%"
            else:
                out[col] = out[col].round(0).astype(int)
    return out


def format_matrix_for_display(df, pct_rows=False):
    out = df.copy()
    year_cols = [c for c in out.columns if str(c).startswith("Año ")]
    for idx, row in out.iterrows():
        is_pct = False
        if "Concepto" in out.columns:
            is_pct = "%" in str(row.get("Concepto", ""))
        for c in year_cols:
            if is_pct:
                out.at[idx, c] = f"{row[c] * 100:.2f}%"
            else:
                out.at[idx, c] = int(round(row[c], 0)) if pd.notnull(row[c]) else 0
    return out


# ============================================================
# UI
# ============================================================

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

explanation_card = dbc.Card(
    [
        dbc.CardHeader(html.H5("Guía de lectura del modelo", className="m-0")),
        dbc.CardBody(
            [
                dbc.Accordion(
                    [
                        dbc.AccordionItem(
                            [
                                html.P("OPEX son los gastos operativos recurrentes necesarios para prestar el servicio: salarios, prestadores PJ, alquiler, contabilidad, asesorías, electricidad, internet, telefonía, seguros, software y bienes de consumo."),
                                html.P("En este modelo el OPEX reduce el EBITDA y la base económica de la operación."),
                            ],
                            title="¿Qué incluye OPEX?",
                        ),
                        dbc.AccordionItem(
                            [
                                html.P("CAPEX es la inversión inicial o salida de caja para instalar la operación: constitución, certificados, sello societario, mobiliario y equipos informáticos."),
                                html.P("Para flujo de caja, el CAPEX se descuenta en el año 1. Para IRE, se separa entre gastos de apertura deducibles y activos fijos depreciables."),
                            ],
                            title="¿Qué incluye CAPEX?",
                        ),
                        dbc.AccordionItem(
                            [
                                html.P("Los gastos de apertura deducibles son constitución EAS, certificado de facturación electrónica y sello societario. Si el switch está activo, reducen la base del IRE en el año 1."),
                                html.P("Los activos fijos, como mobiliario y computadoras, no se deducen completos de una vez: reducen la base del IRE vía depreciación fiscal anual."),
                            ],
                            title="Tratamiento fiscal de CAPEX para IRE",
                        ),
                        dbc.AccordionItem(
                            [
                                html.P("Servicios personales incluye salarios, prestadores PJ, aguinaldo e IPS patronal. Los salarios, aguinaldo e IPS no generan IVA crédito; los prestadores PJ sí generan IVA crédito si facturan con IVA."),
                                html.P("Servicios no personales incluye alquiler, contabilidad, asesorías, costos regulatorios, electricidad, internet, telefonía, seguros y software."),
                            ],
                            title="Servicios personales y no personales",
                        ),
                        dbc.AccordionItem(
                            [
                                html.P("Como la operación se modela como exportación de servicios, no se calcula IVA débito sobre ingresos. Sí se calcula IVA crédito fiscal sobre servicios no personales, prestadores PJ, bienes de consumo y alquiler."),
                                html.P("El IVA crédito se muestra separado. No se trata como OPEX, porque no es un gasto operativo en sentido económico si puede ser recuperado o compensado."),
                            ],
                            title="IVA crédito fiscal",
                        ),
                    ],
                    start_collapsed=True,
                )
            ]
        ),
    ],
    className="shadow-sm mb-4",
)

controls = dbc.Card(
    [
        dbc.CardHeader(html.H5("Calculadora de supuestos", className="m-0")),
        dbc.CardBody(
            [
                html.H6("Horizonte temporal y moneda"),
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
                            md=8,
                            className="mb-4",
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Mostrar resultados en", className="small fw-semibold"),
                                dbc.RadioItems(
                                    id="display_currency",
                                    options=[
                                        {"label": "Reales brasileños (BRL)", "value": "BRL"},
                                        {"label": "Guaraníes (PYG)", "value": "PYG"},
                                    ],
                                    value=DEFAULTS["display_currency"],
                                    inline=False,
                                ),
                            ],
                            md=4,
                            className="mb-4",
                        ),
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
                html.H6("Servicios personales Paraguay"),
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
                html.H6("Servicios no personales y costos operativos Paraguay"),
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
                html.H6("CAPEX, apertura y depreciación fiscal"),
                dbc.Row(
                    [
                        input_number("Constitución EAS", "incorporation_usd", DEFAULTS["incorporation_usd"], 10, 0, "USD"),
                        input_number("Certificado facturación electrónica", "invoice_cert_pyg", DEFAULTS["invoice_cert_pyg"], 10000, 0, "PYG"),
                        input_number("Sello societario", "seal_pyg", DEFAULTS["seal_pyg"], 10000, 0, "PYG"),
                        input_number("Mobiliario/oficina inicial", "office_setup_pyg", DEFAULTS["office_setup_pyg"], 100000, 0, "PYG"),
                        input_number("Vida útil mobiliario/oficina", "office_setup_life_years", DEFAULTS["office_setup_life_years"], 1, 1, "años"),
                        input_number("Cantidad computadoras", "computer_count", DEFAULTS["computer_count"], 1, 0),
                        input_number("Costo unitario computadora", "computer_unit_pyg", DEFAULTS["computer_unit_pyg"], 100000, 0, "PYG"),
                        input_number("Vida útil computadoras", "computer_life_years", DEFAULTS["computer_life_years"], 1, 1, "años"),
                    ]
                ),
                dbc.Checklist(
                    options=[
                        {"label": "Deducir gastos de apertura en el año 1 para base IRE", "value": "deduct"},
                        {"label": "Aplicar depreciación fiscal de activos fijos", "value": "depreciate"},
                    ],
                    value=["deduct", "depreciate"],
                    id="capex_tax_options",
                    switch=True,
                    className="mb-2",
                ),
                html.Hr(),
                html.H6("Impuestos Paraguay"),
                dbc.Row(
                    [
                        input_number("IRE", "ire_rate", DEFAULTS["ire_rate"] * 100, 0.1, 0, "%"),
                        input_number("IDU no residente", "idu_nonresident_rate", DEFAULTS["idu_nonresident_rate"] * 100, 0.1, 0, "%"),
                        input_number("% utilidad distribuida", "dividend_distribution_rate", DEFAULTS["dividend_distribution_rate"] * 100, 1, 0, "%"),
                        input_number("IVA gastos generales", "expense_vat_general", DEFAULTS["expense_vat_general"] * 100, 0.1, 0, "%"),
                        input_number("IVA alquiler comercial", "rent_vat", DEFAULTS["rent_vat"] * 100, 0.1, 0, "%"),
                    ]
                ),
                dbc.Checklist(
                    options=[{"label": "Calcular IVA crédito fiscal", "value": 1}],
                    value=[1],
                    id="calculate_vat_credit",
                    switch=True,
                    className="mb-2",
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
                    "Nota: este modelo es una herramienta de análisis financiero. Validar el encuadre fiscal final con contador/abogado tributario, especialmente IVA exportación de servicios, depreciaciones admitidas, precios de transferencia y retenciones aplicables.",
                    color="warning",
                    className="mt-3",
                ),
                explanation_card,
                controls,
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
                        dbc.Col(dcc.Graph(id="cash_flow_chart"), md=12),
                    ]
                ),
                html.H4("Cuadro general de evolución", className="mt-4"),
                html.P(
                    "Resumen anual por grandes rubros. Permite ver cómo evolucionan ingresos, OPEX, CAPEX, deducciones fiscales, impuestos, márgenes y flujo.",
                    className="text-muted",
                ),
                dash_table.DataTable(
                    id="summary_table",
                    page_size=25,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px", "textAlign": "right"},
                    style_cell_conditional=[{"if": {"column_id": "Concepto"}, "textAlign": "left", "fontWeight": "bold"}],
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
                html.H4("Cuadro detallado por cuenta", className="mt-4"),
                html.P(
                    "Detalle anual por nivel de cuenta. Abre OPEX, CAPEX, deducciones fiscales, impuestos e IVA crédito fiscal.",
                    className="text-muted",
                ),
                dash_table.DataTable(
                    id="detail_table",
                    page_size=20,
                    sort_action="native",
                    filter_action="native",
                    style_table={"overflowX": "auto"},
                    style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px", "textAlign": "right"},
                    style_cell_conditional=[
                        {"if": {"column_id": "Rubro nivel 1"}, "textAlign": "left"},
                        {"if": {"column_id": "Rubro nivel 2"}, "textAlign": "left"},
                        {"if": {"column_id": "Cuenta"}, "textAlign": "left", "fontWeight": "bold"},
                    ],
                    style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"},
                ),
                html.H4("Tabla base del modelo", className="mt-4"),
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
        "display_currency",
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
        "office_setup_life_years",
        "computer_count",
        "computer_unit_pyg",
        "computer_life_years",
        "capex_tax_options",
        "ire_rate",
        "idu_nonresident_rate",
        "dividend_distribution_rate",
        "expense_vat_general",
        "rent_vat",
        "calculate_vat_credit",
        "inflation_py",
    ]
    p = DEFAULTS.copy()
    for k, v in zip(keys, values):
        if k in ["use_payroll", "calculate_vat_credit"]:
            p[k] = bool(v)
        elif k == "capex_tax_options":
            selected = v or []
            p["deduct_startup_expenses_year1"] = "deduct" in selected
            p["depreciate_fixed_assets"] = "depreciate" in selected
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
        elif k in ["years", "employee_count", "contractor_count", "computer_count", "office_setup_life_years", "computer_life_years"]:
            p[k] = max(0, int(v or 0))
        elif k == "display_currency":
            p[k] = v or "BRL"
        else:
            p[k] = v or 0

    p["years"] = max(1, int(p["years"]))
    p["office_setup_life_years"] = max(1, int(p["office_setup_life_years"]))
    p["computer_life_years"] = max(1, int(p["computer_life_years"]))
    p["aguinaldo_rate"] = 1 / 12
    return p


inputs = [
    Input("years", "value"),
    Input("display_currency", "value"),
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
    Input("office_setup_life_years", "value"),
    Input("computer_count", "value"),
    Input("computer_unit_pyg", "value"),
    Input("computer_life_years", "value"),
    Input("capex_tax_options", "value"),
    Input("ire_rate", "value"),
    Input("idu_nonresident_rate", "value"),
    Input("dividend_distribution_rate", "value"),
    Input("expense_vat_general", "value"),
    Input("rent_vat", "value"),
    Input("calculate_vat_credit", "value"),
    Input("inflation_py", "value"),
]


@app.callback(
    Output("kpi_cards", "children"),
    Output("evolution_chart", "figure"),
    Output("margin_chart", "figure"),
    Output("cost_breakdown_chart", "figure"),
    Output("tax_chart", "figure"),
    Output("cash_flow_chart", "figure"),
    Output("summary_table", "data"),
    Output("summary_table", "columns"),
    Output("detail_table", "data"),
    Output("detail_table", "columns"),
    Output("model_table", "data"),
    Output("model_table", "columns"),
    *inputs,
)
def update_dashboard(*values):
    p = collect_params(*values)
    df, detail_df = compute_model(p)

    currency = p["display_currency"]
    prefix = money_prefix(p)

    # Valores display
    df_disp = df.copy()
    money_cols = [c for c in df_disp.columns if c.endswith(" BRL")]
    for col in money_cols:
        df_disp[col.replace(" BRL", f" {currency}")] = df_disp[col].apply(lambda x: display_value(x, p))
        df_disp.drop(columns=[col], inplace=True)

    total_revenue = display_value(df["Ingresos BRL"].sum(), p)
    total_opex = display_value(df["OPEX BRL"].sum(), p)
    total_ebitda = display_value(df["EBITDA BRL"].sum(), p)
    total_net = display_value(df["Resultado neto remitible BRL"].sum(), p)
    total_cash_flow = display_value(df["Flujo de caja neto BRL"].sum(), p)
    avg_margin = df["Margen neto"].mean()
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
        kpi("Ingresos acumulados", fmt_money(total_revenue, p), years_label),
        kpi("OPEX acumulado", fmt_money(total_opex, p), "Gastos operativos recurrentes"),
        kpi("EBITDA acumulado", fmt_money(total_ebitda, p), "Ingresos - OPEX"),
        kpi("Resultado neto acumulado", fmt_money(total_net, p), f"Margen neto promedio: {pct(avg_margin)}"),
        kpi("Flujo de caja acumulado", fmt_money(total_cash_flow, p), "Resultado neto - CAPEX caja"),
    ]

    # Gráfico evolución
    evolution_df = pd.DataFrame({
        "Año": df["Año"],
        f"Ingresos {currency}": df["Ingresos BRL"].apply(lambda x: display_value(x, p)),
        f"OPEX {currency}": df["OPEX BRL"].apply(lambda x: display_value(x, p)),
        f"EBITDA {currency}": df["EBITDA BRL"].apply(lambda x: display_value(x, p)),
        f"Resultado neto remitible {currency}": df["Resultado neto remitible BRL"].apply(lambda x: display_value(x, p)),
    })
    evolution_long = evolution_df.melt(id_vars="Año", var_name="Concepto", value_name=currency)
    fig_evolution = px.line(
        evolution_long,
        x="Año",
        y=currency,
        color="Concepto",
        markers=True,
        template="plotly_white",
        title="Evolución temporal de ingresos, OPEX, EBITDA y resultado neto",
    )
    fig_evolution.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    # Márgenes
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

    # Estructura de egresos
    cost_df = pd.DataFrame({
        "Año": df["Año"],
        "Servicios personales": df["Servicios personales BRL"].apply(lambda x: display_value(x, p)),
        "Servicios no personales": df["Servicios no personales BRL"].apply(lambda x: display_value(x, p)),
        "Bienes consumo e insumos": df["Bienes consumo e insumos BRL"].apply(lambda x: display_value(x, p)),
        "CAPEX caja": df["CAPEX caja BRL"].apply(lambda x: display_value(x, p)),
    })
    cost_long = cost_df.melt(id_vars="Año", var_name="Rubro", value_name=currency)
    fig_cost = px.area(
        cost_long,
        x="Año",
        y=currency,
        color="Rubro",
        template="plotly_white",
        title="Estructura de egresos e inversión",
    )
    fig_cost.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    # Impuestos y fiscal
    tax_df = pd.DataFrame({
        "Año": df["Año"],
        "Gastos apertura deducibles IRE": df["Gastos apertura deducibles IRE BRL"].apply(lambda x: display_value(x, p)),
        "Depreciación fiscal": df["Depreciación fiscal BRL"].apply(lambda x: display_value(x, p)),
        "IRE": df["IRE BRL"].apply(lambda x: display_value(x, p)),
        "IDU": df["IDU BRL"].apply(lambda x: display_value(x, p)),
        "IVA crédito fiscal": df["IVA crédito fiscal BRL"].apply(lambda x: display_value(x, p)),
    })
    tax_long = tax_df.melt(id_vars="Año", var_name="Concepto", value_name=currency)
    fig_tax = px.bar(
        tax_long,
        x="Año",
        y=currency,
        color="Concepto",
        barmode="group",
        template="plotly_white",
        title="Deducciones fiscales, impuestos e IVA crédito",
    )
    fig_tax.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    # Flujo
    cash_df = pd.DataFrame({
        "Año": df["Año"],
        f"Flujo de caja neto {currency}": df["Flujo de caja neto BRL"].apply(lambda x: display_value(x, p)),
        f"Flujo acumulado {currency}": df["Flujo acumulado BRL"].apply(lambda x: display_value(x, p)),
    })
    cash_long = cash_df.melt(id_vars="Año", var_name="Concepto", value_name=currency)
    fig_cash = px.line(
        cash_long,
        x="Año",
        y=currency,
        color="Concepto",
        markers=True,
        template="plotly_white",
        title="Flujo de caja neto y acumulado",
    )
    fig_cash.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    # Tablas
    summary_base = build_summary_table(df)
    summary_display = summary_base.copy()
    for idx, row in summary_display.iterrows():
        is_pct = "%" in str(row["Concepto"])
        for col in [c for c in summary_display.columns if c.startswith("Año ")]:
            if is_pct:
                summary_display.at[idx, col] = f"{float(row[col]) * 100:.2f}%"
            else:
                summary_display.at[idx, col] = int(round(display_value(float(row[col]), p), 0))
    summary_columns = [{"name": c, "id": c} for c in summary_display.columns]

    detail_matrix_base = build_detail_matrix(detail_df)
    detail_display = detail_matrix_base.copy()
    for col in [c for c in detail_display.columns if c.startswith("Año ")]:
        detail_display[col] = detail_display[col].apply(lambda x: int(round(display_value(float(x), p), 0)))
    detail_columns = [{"name": c, "id": c} for c in detail_display.columns]

    model_display = df_disp.copy()
    for col in model_display.columns:
        if col != "Año":
            if col in ["Margen bruto", "Margen EBITDA", "Margen neto"]:
                model_display[col] = (model_display[col] * 100).round(2).astype(str) + "%"
            elif pd.api.types.is_numeric_dtype(model_display[col]):
                model_display[col] = model_display[col].round(0).astype(int)
    model_columns = [{"name": c, "id": c} for c in model_display.columns]

    return (
        cards,
        fig_evolution,
        fig_margin,
        fig_cost,
        fig_tax,
        fig_cash,
        summary_display.to_dict("records"),
        summary_columns,
        detail_display.to_dict("records"),
        detail_columns,
        model_display.to_dict("records"),
        model_columns,
    )


@app.callback(
    Output("download_model", "data"),
    Input("download_btn", "n_clicks"),
    *[State(i.component_id, i.component_property) for i in inputs],
    prevent_initial_call=True,
)
def download_csv(n_clicks, *values):
    p = collect_params(*values)
    df, detail_df = compute_model(p)
    summary = build_summary_table(df)
    detail = build_detail_matrix(detail_df)

    # Exporta tres bloques en un mismo CSV simple.
    lines = []
    lines.append("TABLA BASE DEL MODELO")
    lines.append(df.to_csv(index=False))
    lines.append("\nCUADRO GENERAL DE EVOLUCION")
    lines.append(summary.to_csv(index=False))
    lines.append("\nCUADRO DETALLADO POR CUENTA")
    lines.append(detail.to_csv(index=False))

    content = "\n".join(lines)
    return dict(content=content, filename="modelo_operacion_paraguay.csv")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
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
    "computer_count": 8,
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
