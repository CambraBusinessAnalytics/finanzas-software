import os
import pandas as pd
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table

# ============================================================
# DASHBOARD FINANCIERO: OPERACIÓN PARAGUAY
# Horizonte editable | Moneda de presentación: BRL / PYG
#
# Lógica corregida:
# - OPEX reduce EBITDA.
# - CAPEX caja se muestra como desembolso de inversión.
# - Gastos de apertura deducibles y depreciación fiscal reducen la base del IRE.
# - El flujo de caja se calcula por caja: EBITDA - CAPEX caja - IRE - IDU.
# ============================================================

APP_TITLE = "Análisis financiero: operación en Paraguay"

DEFAULTS = {
    "years": 10,
    "annual_revenue_brl": 9_500_000,
    "revenue_growth": 0.03,
    "pyg_per_brl": 1150,
    "pyg_per_usd": 6100,
    "inflation_py": 0.04,

    # Servicios personales
    "employee_count": 3,
    "monthly_salary_pyg": 3_000_000,
    "contractor_count": 1,
    "monthly_contractor_fee_pyg": 7_000_000,
    "use_payroll": True,
    "ips_employer": 0.165,
    "aguinaldo_rate": 1 / 12,

    # Servicios no personales / costos operativos
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

    # CAPEX / inversión inicial
    "incorporation_usd": 400,
    "invoice_cert_pyg": 480_000,
    "seal_pyg": 130_000,
    "office_setup_pyg": 10_000_000,
    "computer_count": 8,
    "computer_unit_pyg": 3_000_000,

    # Tratamiento fiscal del CAPEX
    "deduct_startup_expenses_year1": True,
    "depreciate_fixed_assets": True,
    "office_setup_life_years": 5,
    "computer_life_years": 4,

    # Impuestos / IVA crédito
    "ire_rate": 0.10,
    "idu_nonresident_rate": 0.15,
    "dividend_distribution_rate": 1.00,
    "expense_vat_general": 0.10,
    "rent_vat": 0.10,
    "calculate_vat_credit": True,
}


def brl_from_pyg(value_pyg, pyg_per_brl):
    return 0 if pyg_per_brl <= 0 else value_pyg / pyg_per_brl


def brl_from_usd(value_usd, pyg_per_usd, pyg_per_brl):
    return brl_from_pyg(value_usd * pyg_per_usd, pyg_per_brl)


def from_brl(value_brl, currency, pyg_per_brl):
    return value_brl * pyg_per_brl if currency == "PYG" else value_brl


def currency_prefix(currency):
    return "Gs. " if currency == "PYG" else "R$ "


def fmt_money(value, currency="BRL"):
    return f"{currency_prefix(currency)}{value:,.0f}".replace(",", ".")


def safe_div(a, b):
    return a / b if b else 0


def compute_model(p):
    years = max(1, int(p["years"]))
    rows = []
    detail_rows = []

    incorporation_brl = brl_from_usd(p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"])
    invoice_cert_brl = brl_from_pyg(p["invoice_cert_pyg"], p["pyg_per_brl"])
    seal_brl = brl_from_pyg(p["seal_pyg"], p["pyg_per_brl"])
    startup_expenses_brl = incorporation_brl + invoice_cert_brl + seal_brl

    office_setup_brl = brl_from_pyg(p["office_setup_pyg"], p["pyg_per_brl"])
    computer_assets_brl = brl_from_pyg(p["computer_count"] * p["computer_unit_pyg"], p["pyg_per_brl"])
    fixed_assets_brl = office_setup_brl + computer_assets_brl
    total_initial_capex_brl = startup_expenses_brl + fixed_assets_brl

    office_dep_annual_brl = safe_div(office_setup_brl, max(1, int(p["office_setup_life_years"])))
    computer_dep_annual_brl = safe_div(computer_assets_brl, max(1, int(p["computer_life_years"])))

    for y in range(1, years + 1):
        py_infl = (1 + p["inflation_py"]) ** (y - 1)
        revenue_brl = p["annual_revenue_brl"] * ((1 + p["revenue_growth"]) ** (y - 1))

        # Servicios personales
        salary_brl = brl_from_pyg(p["employee_count"] * p["monthly_salary_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        contractors_brl = brl_from_pyg(p["contractor_count"] * p["monthly_contractor_fee_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        aguinaldo_brl = salary_brl * p["aguinaldo_rate"] if p["use_payroll"] else 0
        ips_brl = salary_brl * p["ips_employer"] if p["use_payroll"] else 0
        personal_brl = salary_brl + contractors_brl + aguinaldo_brl + ips_brl

        # Servicios no personales
        rent_brl = brl_from_pyg(p["monthly_office_rent_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        accounting_brl = brl_from_pyg(p["accounting_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        advisory_brl = brl_from_pyg(p["advisory_annual_pyg"] * py_infl, p["pyg_per_brl"])
        regulatory_brl = brl_from_pyg(p["regulatory_annual_pyg"] * py_infl, p["pyg_per_brl"])
        utilities_brl = brl_from_pyg(p["utilities_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        internet_brl = brl_from_pyg(p["internet_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        phone_brl = brl_from_pyg(p["phone_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        insurance_brl = brl_from_pyg(p["insurance_annual_pyg"] * py_infl, p["pyg_per_brl"])
        software_brl = brl_from_pyg(p["software_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])
        non_personal_brl = rent_brl + accounting_brl + advisory_brl + regulatory_brl + utilities_brl + internet_brl + phone_brl + insurance_brl + software_brl

        # Bienes de consumo
        supplies_brl = brl_from_pyg(p["supplies_monthly_pyg"] * 12 * py_infl, p["pyg_per_brl"])

        # IVA crédito fiscal: no es OPEX; se muestra separado.
        vat_general_base_brl = contractors_brl + accounting_brl + advisory_brl + regulatory_brl + utilities_brl + internet_brl + phone_brl + insurance_brl + software_brl + supplies_brl
        vat_credit_general_brl = vat_general_base_brl * p["expense_vat_general"] if p["calculate_vat_credit"] else 0
        vat_credit_rent_brl = rent_brl * p["rent_vat"] if p["calculate_vat_credit"] else 0
        vat_credit_brl = vat_credit_general_brl + vat_credit_rent_brl

        # EBITDA y base fiscal
        opex_brl = personal_brl + non_personal_brl + supplies_brl
        gross_profit_brl = revenue_brl - personal_brl - software_brl
        ebitda_brl = revenue_brl - opex_brl

        startup_deductible_brl = startup_expenses_brl if (y == 1 and p["deduct_startup_expenses_year1"]) else 0
        office_dep_brl = office_dep_annual_brl if (p["depreciate_fixed_assets"] and y <= int(p["office_setup_life_years"])) else 0
        computer_dep_brl = computer_dep_annual_brl if (p["depreciate_fixed_assets"] and y <= int(p["computer_life_years"])) else 0
        depreciation_brl = office_dep_brl + computer_dep_brl

        result_before_ire_brl = ebitda_brl - startup_deductible_brl - depreciation_brl
        ire_brl = max(0, result_before_ire_brl * p["ire_rate"])
        result_after_ire_brl = result_before_ire_brl - ire_brl
        idu_brl = max(0, result_after_ire_brl * p["dividend_distribution_rate"] * p["idu_nonresident_rate"])
        net_remitted_brl = result_after_ire_brl - idu_brl

        capex_cash_brl = total_initial_capex_brl if y == 1 else 0
        cash_flow_brl = ebitda_brl - capex_cash_brl - ire_brl - idu_brl

        row = {
            "Año": y,
            "Ingresos BRL": revenue_brl,
            "Servicios personales BRL": personal_brl,
            "Servicios no personales BRL": non_personal_brl,
            "Bienes consumo e insumos BRL": supplies_brl,
            "OPEX BRL": opex_brl,
            "Margen bruto BRL": gross_profit_brl,
            "EBITDA BRL": ebitda_brl,
            "Gastos apertura deducibles IRE BRL": startup_deductible_brl,
            "Depreciación fiscal BRL": depreciation_brl,
            "Resultado antes de IRE BRL": result_before_ire_brl,
            "IRE BRL": ire_brl,
            "Resultado después de IRE BRL": result_after_ire_brl,
            "IDU BRL": idu_brl,
            "Resultado neto remitible BRL": net_remitted_brl,
            "CAPEX caja BRL": capex_cash_brl,
            "Flujo de caja neto BRL": cash_flow_brl,
            "IVA crédito fiscal BRL": vat_credit_brl,
            "IVA crédito general BRL": vat_credit_general_brl,
            "IVA crédito alquiler BRL": vat_credit_rent_brl,
            "Margen bruto": safe_div(gross_profit_brl, revenue_brl),
            "Margen EBITDA": safe_div(ebitda_brl, revenue_brl),
            "Margen neto": safe_div(net_remitted_brl, revenue_brl),
        }
        rows.append(row)

        account_details = [
            ("Ingresos", "Facturación", "Ingresos por exportación de servicios", revenue_brl),
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
            ("CAPEX caja", "Gastos de apertura", "Constitución EAS", incorporation_brl if y == 1 else 0),
            ("CAPEX caja", "Gastos de apertura", "Certificado facturación electrónica", invoice_cert_brl if y == 1 else 0),
            ("CAPEX caja", "Gastos de apertura", "Sello societario", seal_brl if y == 1 else 0),
            ("CAPEX caja", "Activos fijos", "Mobiliario / oficina inicial", office_setup_brl if y == 1 else 0),
            ("CAPEX caja", "Activos fijos", "Equipos informáticos", computer_assets_brl if y == 1 else 0),
            ("Deducciones fiscales", "Gastos de apertura", "Gastos de apertura deducibles IRE", startup_deductible_brl),
            ("Deducciones fiscales", "Depreciación fiscal", "Depreciación mobiliario / oficina", office_dep_brl),
            ("Deducciones fiscales", "Depreciación fiscal", "Depreciación equipos informáticos", computer_dep_brl),
            ("Fiscal", "IVA crédito", "IVA crédito general", vat_credit_general_brl),
            ("Fiscal", "IVA crédito", "IVA crédito alquiler", vat_credit_rent_brl),
            ("Impuestos", "IRE", "IRE sobre resultado antes de IRE", ire_brl),
            ("Impuestos", "IDU", "IDU sobre utilidad distribuida", idu_brl),
            ("Resultado", "Resultado", "Resultado neto remitible", net_remitted_brl),
            ("Resultado", "Flujo", "Flujo de caja neto", cash_flow_brl),
        ]
        for rubro1, rubro2, cuenta, value in account_details:
            detail_rows.append({"Año": y, "Rubro nivel 1": rubro1, "Rubro nivel 2": rubro2, "Cuenta": cuenta, "Valor BRL": value})

    df = pd.DataFrame(rows)
    df["Flujo acumulado BRL"] = df["Flujo de caja neto BRL"].cumsum()

    detail_df = pd.DataFrame(detail_rows)
    accumulated = df[["Año", "Flujo acumulado BRL"]].copy()
    for _, row in accumulated.iterrows():
        detail_df.loc[len(detail_df)] = {
            "Año": int(row["Año"]),
            "Rubro nivel 1": "Resultado",
            "Rubro nivel 2": "Flujo",
            "Cuenta": "Flujo acumulado",
            "Valor BRL": row["Flujo acumulado BRL"],
        }

    return df, detail_df


def convert_money_columns(df, currency, pyg_per_brl):
    """Convierte columnas monetarias base BRL a la moneda de presentación.

    Importante: si currency == "BRL", el nombre nuevo coincide con el original.
    En ese caso NO se debe crear y luego eliminar la misma columna, porque eso
    deja el DataFrame sin columnas monetarias y rompe gráficos/tablas.
    """
    out = df.copy()
    for col in list(out.columns):
        if col.endswith(" BRL"):
            new_col = col.replace(" BRL", f" {currency}")
            converted = out[col].apply(lambda x: from_brl(x, currency, pyg_per_brl))
            if new_col == col:
                out[col] = converted
            else:
                out[new_col] = converted
                out.drop(columns=[col], inplace=True)
    return out


def format_for_display(df):
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]) and col != "Año":
            if "Margen" in col and not col.endswith(("BRL", "PYG")):
                out[col] = (out[col] * 100).round(2).astype(str) + "%"
            else:
                out[col] = out[col].round(0).astype(int)
    return out


def build_summary_matrix(df):
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
        ("Resultado antes de IRE", "Resultado antes de IRE BRL"),
        ("IRE", "IRE BRL"),
        ("Resultado después de IRE", "Resultado después de IRE BRL"),
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
    rows = []
    for label, col in mapping:
        row = {"Concepto": label}
        for _, r in df.iterrows():
            row[f"Año {int(r['Año'])}"] = r[col]
        rows.append(row)
    return pd.DataFrame(rows)


def build_detail_matrix(detail_df):
    matrix = detail_df.pivot_table(index=["Rubro nivel 1", "Rubro nivel 2", "Cuenta"], columns="Año", values="Valor BRL", aggfunc="sum", fill_value=0).reset_index()
    matrix.columns = [f"Año {int(c)}" if isinstance(c, int) or str(c).isdigit() else c for c in matrix.columns]
    return matrix


def convert_matrix_values(matrix, currency, pyg_per_brl):
    out = matrix.copy()
    year_cols = [c for c in out.columns if str(c).startswith("Año ")]
    for idx, row in out.iterrows():
        is_pct = "%" in str(row.get("Concepto", ""))
        for col in year_cols:
            val = float(row[col]) if pd.notnull(row[col]) else 0
            out.at[idx, col] = f"{val * 100:.2f}%" if is_pct else int(round(from_brl(val, currency, pyg_per_brl), 0))
    return out


def input_number(label, id_, value, step=1, min_=0, suffix=None):
    return dbc.Col([
        dbc.Label(label, className="small fw-semibold"),
        dbc.InputGroup([
            dbc.Input(id=id_, type="number", value=value, step=step, min=min_),
            dbc.InputGroupText(suffix) if suffix else html.Span(),
        ]),
    ], md=3, sm=6, xs=12, className="mb-3")


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

explanatory_notes = dbc.Accordion([
    dbc.AccordionItem([
        html.P("OPEX son los gastos operativos recurrentes necesarios para prestar el servicio: salarios, prestadores PJ, alquiler, contabilidad, asesorías, electricidad, internet, telefonía, seguros, software y bienes de consumo."),
        html.P("CAPEX es inversión o salida de caja inicial: constitución, certificado de facturación electrónica, sello societario, mobiliario y equipos informáticos."),
        html.P("En este modelo el CAPEX se muestra como salida de caja en el año 1. Para IRE, se separa entre gastos de apertura deducibles y activos fijos que se deducen vía depreciación fiscal."),
    ], title="Qué significan OPEX y CAPEX"),
    dbc.AccordionItem([
        html.P("Servicios personales incluye salarios, prestadores PJ, aguinaldo e IPS patronal. Los salarios, aguinaldo e IPS no generan IVA crédito; los prestadores PJ sí generan IVA crédito si facturan servicios gravados."),
        html.P("Servicios no personales incluye alquiler, contabilidad, asesorías, costos regulatorios, electricidad, internet, telefonía, seguros y software."),
    ], title="Servicios personales y no personales"),
    dbc.AccordionItem([
        html.P("Como se modela una exportación de servicios, no se calcula IVA débito sobre ingresos. Sí se estima IVA crédito fiscal por compras y servicios gravados: prestadores PJ, servicios no personales, bienes de consumo y alquiler."),
        html.P("El IVA crédito se muestra separado y no se incluye en OPEX."),
    ], title="IVA crédito fiscal"),
    dbc.AccordionItem([
        html.P("EBITDA = ingresos - OPEX."),
        html.P("Resultado antes de IRE = EBITDA - gastos de apertura deducibles - depreciación fiscal."),
        html.P("IRE = resultado antes de IRE × tasa IRE, si el resultado es positivo."),
        html.P("Flujo de caja neto = EBITDA - CAPEX caja - IRE - IDU."),
    ], title="Fórmulas principales"),
], start_collapsed=True, className="mb-4")

controls = dbc.Card([
    dbc.CardHeader(html.H5("Calculadora de supuestos", className="m-0")),
    dbc.CardBody([
        html.H6("Horizonte temporal y moneda"),
        dbc.Row([
            dbc.Col([
                dbc.Label("Años de proyección", className="small fw-semibold"),
                dcc.Slider(id="years", min=1, max=20, step=1, value=DEFAULTS["years"], marks={i: str(i) for i in range(1, 21)}, tooltip={"placement": "bottom", "always_visible": True}),
            ], md=8, className="mb-4"),
            dbc.Col([
                dbc.Label("Mostrar resultados en", className="small fw-semibold"),
                dbc.RadioItems(id="display_currency", options=[{"label": "Reales brasileños (BRL)", "value": "BRL"}, {"label": "Guaraníes (PYG)", "value": "PYG"}], value="BRL"),
            ], md=4, className="mb-4"),
        ]),
        html.Hr(),
        html.H6("Ingresos y tipo de cambio"),
        dbc.Row([
            input_number("Facturación anual inicial", "annual_revenue_brl", DEFAULTS["annual_revenue_brl"], 100000, 0, "BRL"),
            input_number("Crecimiento anual ingresos", "revenue_growth", DEFAULTS["revenue_growth"] * 100, 0.5, -100, "%"),
            input_number("PYG por BRL", "pyg_per_brl", DEFAULTS["pyg_per_brl"], 10, 1),
            input_number("PYG por USD", "pyg_per_usd", DEFAULTS["pyg_per_usd"], 10, 1),
        ]),
        html.Hr(),
        html.H6("Servicios personales"),
        dbc.Row([
            input_number("Funcionarios", "employee_count", DEFAULTS["employee_count"], 1, 0),
            input_number("Salario mensual por funcionario", "monthly_salary_pyg", DEFAULTS["monthly_salary_pyg"], 100000, 0, "PYG"),
            input_number("Prestadores PJ", "contractor_count", DEFAULTS["contractor_count"], 1, 0),
            input_number("Fee mensual PJ", "monthly_contractor_fee_pyg", DEFAULTS["monthly_contractor_fee_pyg"], 100000, 0, "PYG"),
            input_number("IPS patronal", "ips_employer", DEFAULTS["ips_employer"] * 100, 0.1, 0, "%"),
        ]),
        dbc.Checklist(options=[{"label": "Incluir aguinaldo e IPS para funcionarios en relación de dependencia", "value": 1}], value=[1], id="use_payroll", switch=True, className="mb-2"),
        html.Hr(),
        html.H6("Servicios no personales y costos operativos"),
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
        html.H6("CAPEX, apertura y depreciación fiscal"),
        dbc.Row([
            input_number("Constitución EAS", "incorporation_usd", DEFAULTS["incorporation_usd"], 10, 0, "USD"),
            input_number("Certificado facturación electrónica", "invoice_cert_pyg", DEFAULTS["invoice_cert_pyg"], 10000, 0, "PYG"),
            input_number("Sello societario", "seal_pyg", DEFAULTS["seal_pyg"], 10000, 0, "PYG"),
            input_number("Mobiliario/oficina inicial", "office_setup_pyg", DEFAULTS["office_setup_pyg"], 100000, 0, "PYG"),
            input_number("Vida útil mobiliario/oficina", "office_setup_life_years", DEFAULTS["office_setup_life_years"], 1, 1, "años"),
            input_number("Cantidad computadoras", "computer_count", DEFAULTS["computer_count"], 1, 0),
            input_number("Costo unitario computadora", "computer_unit_pyg", DEFAULTS["computer_unit_pyg"], 100000, 0, "PYG"),
            input_number("Vida útil computadoras", "computer_life_years", DEFAULTS["computer_life_years"], 1, 1, "años"),
        ]),
        dbc.Checklist(options=[{"label": "Deducir gastos de apertura en año 1 para base IRE", "value": "deduct"}, {"label": "Aplicar depreciación fiscal de activos fijos", "value": "depreciate"}], value=["deduct", "depreciate"], id="capex_tax_options", switch=True, className="mb-2"),
        html.Hr(),
        html.H6("Impuestos Paraguay e IVA crédito"),
        dbc.Row([
            input_number("IRE", "ire_rate", DEFAULTS["ire_rate"] * 100, 0.1, 0, "%"),
            input_number("IDU no residente", "idu_nonresident_rate", DEFAULTS["idu_nonresident_rate"] * 100, 0.1, 0, "%"),
            input_number("% utilidad distribuida", "dividend_distribution_rate", DEFAULTS["dividend_distribution_rate"] * 100, 1, 0, "%"),
            input_number("IVA crédito gastos generales", "expense_vat_general", DEFAULTS["expense_vat_general"] * 100, 0.1, 0, "%"),
            input_number("IVA crédito alquiler", "rent_vat", DEFAULTS["rent_vat"] * 100, 0.1, 0, "%"),
        ]),
        dbc.Checklist(options=[{"label": "Calcular IVA crédito fiscal", "value": 1}], value=[1], id="calculate_vat_credit", switch=True, className="mb-2"),
        html.Hr(),
        html.H6("Actualización temporal de costos"),
        dbc.Row([input_number("Inflación anual costos Paraguay", "inflation_py", DEFAULTS["inflation_py"] * 100, 0.5, 0, "%")]),
    ]),
], className="shadow-sm mb-4")

app.layout = html.Div([
    html.Header(dbc.Container([dbc.Row([dbc.Col([html.H1(APP_TITLE, className="m-0", style={"fontFamily": "Avenir, Arial, sans-serif", "fontWeight": "700", "fontSize": "2rem", "color": "#333"}), html.P("Modelo editable para proyectar ingresos, egresos, impuestos, EBITDA, márgenes y flujo de caja de la operación paraguaya.", className="text-muted mb-0")], md=10)], justify="center", className="py-4")]), style={"backgroundColor": "white", "borderBottom": "1px solid #eee"}),
    dbc.Container([
        dbc.Alert("Nota: este modelo es una herramienta de análisis financiero. Validar el encuadre fiscal final con contador/abogado tributario, especialmente IVA crédito de exportadores, depreciaciones admitidas, precios de transferencia y retenciones aplicables.", color="warning", className="mt-3"),
        explanatory_notes,
        controls,
        dbc.Row(id="kpi_cards", className="g-3 mb-4"),
        dbc.Row([dbc.Col(dcc.Graph(id="evolution_chart"), md=8), dbc.Col(dcc.Graph(id="margin_chart"), md=4)]),
        dbc.Row([dbc.Col(dcc.Graph(id="cost_breakdown_chart"), md=6), dbc.Col(dcc.Graph(id="tax_chart"), md=6)]),
        dbc.Row([dbc.Col(dcc.Graph(id="cash_flow_chart"), md=12)]),
        html.H4("Cuadro general de evolución", className="mt-4"),
        html.P("Resumen anual por grandes rubros. Permite ver ingresos, OPEX, CAPEX, deducciones fiscales, impuestos, márgenes y flujo.", className="text-muted"),
        dash_table.DataTable(id="summary_table", page_size=25, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px", "textAlign": "right"}, style_cell_conditional=[{"if": {"column_id": "Concepto"}, "textAlign": "left", "fontWeight": "bold"}], style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"}),
        html.H4("Cuadro detallado por cuenta", className="mt-4"),
        html.P("Detalle anual por cuenta. Abre OPEX, CAPEX, deducciones fiscales, impuestos e IVA crédito fiscal.", className="text-muted"),
        dash_table.DataTable(id="detail_table", page_size=25, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px", "textAlign": "right"}, style_cell_conditional=[{"if": {"column_id": "Rubro nivel 1"}, "textAlign": "left"}, {"if": {"column_id": "Rubro nivel 2"}, "textAlign": "left"}, {"if": {"column_id": "Cuenta"}, "textAlign": "left", "fontWeight": "bold"}], style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"}),
        html.H4("Tabla base del modelo", className="mt-4"),
        dash_table.DataTable(id="model_table", page_size=10, sort_action="native", filter_action="native", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "8px"}, style_header={"fontWeight": "bold", "backgroundColor": "#f8f9fa"}),
        dcc.Download(id="download_model"),
        dbc.Button("Descargar CSV del escenario", id="download_btn", color="primary", className="my-3"),
    ], fluid=True),
], style={"backgroundColor": "#f7f8fa", "minHeight": "100vh"})


def collect_params(*values):
    keys = [
        "years", "display_currency", "annual_revenue_brl", "revenue_growth", "pyg_per_brl", "pyg_per_usd",
        "employee_count", "monthly_salary_pyg", "contractor_count", "monthly_contractor_fee_pyg", "ips_employer", "use_payroll",
        "monthly_office_rent_pyg", "accounting_monthly_pyg", "advisory_annual_pyg", "regulatory_annual_pyg", "utilities_monthly_pyg", "internet_monthly_pyg", "phone_monthly_pyg", "insurance_annual_pyg", "supplies_monthly_pyg", "software_monthly_pyg",
        "incorporation_usd", "invoice_cert_pyg", "seal_pyg", "office_setup_pyg", "office_setup_life_years", "computer_count", "computer_unit_pyg", "computer_life_years", "capex_tax_options",
        "ire_rate", "idu_nonresident_rate", "dividend_distribution_rate", "expense_vat_general", "rent_vat", "calculate_vat_credit", "inflation_py",
    ]
    p = DEFAULTS.copy()
    for k, v in zip(keys, values):
        if k in ["use_payroll", "calculate_vat_credit"]:
            p[k] = bool(v)
        elif k == "capex_tax_options":
            selected = v or []
            p["deduct_startup_expenses_year1"] = "deduct" in selected
            p["depreciate_fixed_assets"] = "depreciate" in selected
        elif k in ["revenue_growth", "ips_employer", "ire_rate", "idu_nonresident_rate", "dividend_distribution_rate", "expense_vat_general", "rent_vat", "inflation_py"]:
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
    Input("years", "value"), Input("display_currency", "value"), Input("annual_revenue_brl", "value"), Input("revenue_growth", "value"), Input("pyg_per_brl", "value"), Input("pyg_per_usd", "value"),
    Input("employee_count", "value"), Input("monthly_salary_pyg", "value"), Input("contractor_count", "value"), Input("monthly_contractor_fee_pyg", "value"), Input("ips_employer", "value"), Input("use_payroll", "value"),
    Input("monthly_office_rent_pyg", "value"), Input("accounting_monthly_pyg", "value"), Input("advisory_annual_pyg", "value"), Input("regulatory_annual_pyg", "value"), Input("utilities_monthly_pyg", "value"), Input("internet_monthly_pyg", "value"), Input("phone_monthly_pyg", "value"), Input("insurance_annual_pyg", "value"), Input("supplies_monthly_pyg", "value"), Input("software_monthly_pyg", "value"),
    Input("incorporation_usd", "value"), Input("invoice_cert_pyg", "value"), Input("seal_pyg", "value"), Input("office_setup_pyg", "value"), Input("office_setup_life_years", "value"), Input("computer_count", "value"), Input("computer_unit_pyg", "value"), Input("computer_life_years", "value"), Input("capex_tax_options", "value"),
    Input("ire_rate", "value"), Input("idu_nonresident_rate", "value"), Input("dividend_distribution_rate", "value"), Input("expense_vat_general", "value"), Input("rent_vat", "value"), Input("calculate_vat_credit", "value"), Input("inflation_py", "value"),
]


@app.callback(
    Output("kpi_cards", "children"), Output("evolution_chart", "figure"), Output("margin_chart", "figure"), Output("cost_breakdown_chart", "figure"), Output("tax_chart", "figure"), Output("cash_flow_chart", "figure"), Output("summary_table", "data"), Output("summary_table", "columns"), Output("detail_table", "data"), Output("detail_table", "columns"), Output("model_table", "data"), Output("model_table", "columns"),
    *inputs,
)
def update_dashboard(*values):
    p = collect_params(*values)
    df, detail_df = compute_model(p)
    currency = p["display_currency"]
    prefix = currency_prefix(currency)

    df_disp = convert_money_columns(df, currency, p["pyg_per_brl"])
    money = lambda x: fmt_money(from_brl(x, currency, p["pyg_per_brl"]), currency)
    years_label = f"{p['years']} año" if p["years"] == 1 else f"{p['years']} años"

    def kpi(title, value, subtitle=""):
        return dbc.Col(dbc.Card(dbc.CardBody([html.Div(title, className="text-muted small"), html.H3(value, className="mb-1"), html.Div(subtitle, className="small text-muted")]), className="shadow-sm border-0"), md=3, sm=6)

    cards = [
        kpi("Ingresos acumulados", money(df["Ingresos BRL"].sum()), years_label),
        kpi("OPEX acumulado", money(df["OPEX BRL"].sum()), "Gastos operativos"),
        kpi("EBITDA acumulado", money(df["EBITDA BRL"].sum()), "Ingresos - OPEX"),
        kpi("Resultado neto acumulado", money(df["Resultado neto remitible BRL"].sum()), f"Margen neto promedio: {df['Margen neto'].mean() * 100:.1f}%"),
        kpi("Flujo acumulado", money(df["Flujo acumulado BRL"].iloc[-1]), "EBITDA - CAPEX - IRE - IDU"),
        kpi("IVA crédito acumulado", money(df["IVA crédito fiscal BRL"].sum()), "No incluye IVA débito"),
    ]

    evolution_cols = [f"Ingresos {currency}", f"OPEX {currency}", f"EBITDA {currency}", f"Resultado neto remitible {currency}"]
    fig_evolution = px.line(df_disp.melt(id_vars="Año", value_vars=evolution_cols, var_name="Concepto", value_name=currency), x="Año", y=currency, color="Concepto", markers=True, template="plotly_white", title="Evolución temporal de ingresos, OPEX, EBITDA y resultado neto")
    fig_evolution.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    margin_long = df.melt(id_vars="Año", value_vars=["Margen bruto", "Margen EBITDA", "Margen neto"], var_name="Indicador", value_name="Margen")
    fig_margin = px.line(margin_long, x="Año", y="Margen", color="Indicador", markers=True, template="plotly_white", title="Evolución de márgenes")
    fig_margin.update_layout(legend_title_text="", yaxis_tickformat=".1%", title_font=dict(size=18))

    cost_cols = [f"Servicios personales {currency}", f"Servicios no personales {currency}", f"Bienes consumo e insumos {currency}", f"CAPEX caja {currency}"]
    fig_cost = px.area(df_disp.melt(id_vars="Año", value_vars=cost_cols, var_name="Rubro", value_name=currency), x="Año", y=currency, color="Rubro", template="plotly_white", title="Estructura de egresos e inversión")
    fig_cost.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    tax_cols = [f"Gastos apertura deducibles IRE {currency}", f"Depreciación fiscal {currency}", f"IRE {currency}", f"IDU {currency}", f"IVA crédito fiscal {currency}"]
    fig_tax = px.bar(df_disp.melt(id_vars="Año", value_vars=tax_cols, var_name="Concepto", value_name=currency), x="Año", y=currency, color="Concepto", barmode="group", template="plotly_white", title="Deducciones fiscales, impuestos e IVA crédito")
    fig_tax.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    cash_cols = [f"Flujo de caja neto {currency}", f"Flujo acumulado {currency}"]
    fig_cash = px.line(df_disp.melt(id_vars="Año", value_vars=cash_cols, var_name="Concepto", value_name=currency), x="Año", y=currency, color="Concepto", markers=True, template="plotly_white", title="Flujo de caja neto y acumulado")
    fig_cash.update_layout(legend_title_text="", yaxis_tickprefix=prefix, title_font=dict(size=18))

    summary = convert_matrix_values(build_summary_matrix(df), currency, p["pyg_per_brl"])
    summary_columns = [{"name": c, "id": c} for c in summary.columns]

    detail = build_detail_matrix(detail_df)
    detail_display = convert_matrix_values(detail, currency, p["pyg_per_brl"])
    detail_columns = [{"name": c, "id": c} for c in detail_display.columns]

    model_display = format_for_display(df_disp)
    model_columns = [{"name": c, "id": c} for c in model_display.columns]

    return cards, fig_evolution, fig_margin, fig_cost, fig_tax, fig_cash, summary.to_dict("records"), summary_columns, detail_display.to_dict("records"), detail_columns, model_display.to_dict("records"), model_columns


@app.callback(
    Output("download_model", "data"),
    Input("download_btn", "n_clicks"),
    *[State(i.component_id, i.component_property) for i in inputs],
    prevent_initial_call=True,
)
def download_csv(n_clicks, *values):
    p = collect_params(*values)
    df, detail_df = compute_model(p)
    currency = p["display_currency"]
    model = convert_money_columns(df, currency, p["pyg_per_brl"])
    summary = convert_matrix_values(build_summary_matrix(df), currency, p["pyg_per_brl"])
    detail = convert_matrix_values(build_detail_matrix(detail_df), currency, p["pyg_per_brl"])
    content = "TABLA BASE DEL MODELO\n" + model.to_csv(index=False) + "\nCUADRO GENERAL DE EVOLUCION\n" + summary.to_csv(index=False) + "\nCUADRO DETALLADO POR CUENTA\n" + detail.to_csv(index=False)
    return {"content": content, "filename": f"modelo_operacion_paraguay_{currency.lower()}.csv"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False)
