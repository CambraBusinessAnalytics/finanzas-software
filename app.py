import os
import pandas as pd
import plotly.express as px
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, dash_table, ALL

DEFAULTS = {
    "years": 10, "display_currency": "BRL", "language": "PT",
    "annual_revenue_brl": 9_500_000, "revenue_growth": 0.00,
    "pyg_per_brl": 1150, "pyg_per_usd": 6100, "inflation_py": 0.04,
    "employee_count": 3, "monthly_salary_pyg": 3_000_000,
    "contractor_count": 1, "monthly_contractor_fee_pyg": 7_000_000,
    "brazilian_provider_count": 0, "monthly_brazilian_provider_fee_brl": 8_000,
    "use_payroll": True, "ips_employer": 0.165, "aguinaldo_rate": 1/12,
    "monthly_office_rent_pyg": 1_500_000, "accounting_monthly_pyg": 4_000_000,
    "advisory_annual_pyg": 24_000_000, "regulatory_annual_pyg": 8_000_000,
    "utilities_monthly_pyg": 1_200_000, "internet_monthly_pyg": 350_000,
    "phone_monthly_pyg": 250_000, "insurance_annual_pyg": 6_000_000,
    "supplies_monthly_pyg": 600_000, "software_monthly_pyg": 2_500_000,
    "incorporation_usd": 400, "invoice_cert_pyg": 480_000, "seal_pyg": 130_000,
    "office_setup_pyg": 10_000_000, "computer_count": 4, "computer_unit_pyg": 3_000_000,
    "deduct_startup_expenses_year1": True, "depreciate_fixed_assets": True,
    "office_setup_life_years": 5, "computer_life_years": 4,
    "ire_rate": 0.10, "idu_rate_resident": 0.08, "idu_rate_nonresident": 0.15,
    "idu_residency_status": "nonresident", "dividend_distribution_rate": 1.00,
    "expense_vat_general": 0.10, "rent_vat": 0.10, "calculate_vat_credit": True,
}

TEXT = {
"PT": {
"app_title":"Análise financeira: operação no Paraguai","subtitle":"Modelo editável para projetar receitas, custos, impostos, EBITDA, margens e fluxo de caixa da operação paraguaia.",
"note":"Nota: validar o enquadramento fiscal final com contador/advogado tributário, especialmente IVA crédito de exportadores, residência fiscal dos sócios, preços de transferência e retenções aplicáveis.",
"settings":"Calculadora de premissas","guide":"Guia de leitura do modelo","time_currency":"Horizonte temporal, idioma e moeda","language":"Idioma","currency":"Moeda de apresentação","years":"Anos de projeção",
"income_fx":"Receita e câmbio","annual_revenue":"Faturamento anual inicial","revenue_growth":"Crescimento anual da receita","pyg_per_brl":"PYG por BRL","pyg_per_usd":"PYG por USD",
"personal":"Serviços pessoais","employees":"Funcionários","salary":"Salário mensal por funcionário","py_contractors":"Prestadores PJ no Paraguai","py_fee":"Fee mensal PJ Paraguai","br_providers":"Prestadores de serviços brasileiros","br_fee":"Remuneração média mensal por prestador brasileiro","ips":"IPS patronal","use_payroll":"Incluir aguinaldo/13º e IPS para funcionários em relação de dependência",
"non_personal":"Serviços não pessoais e custos operacionais","rent":"Aluguel mensal do escritório","accounting":"Contabilidade mensal","advisory":"Assessorias anuais","regulatory":"Custos regulatórios anuais","utilities":"Energia/serviços mensais","internet":"Internet mensal","phone":"Telefonia mensal","insurance":"Seguros anuais","supplies":"Papelaria/consumo mensal","software":"Software mensal",
"capex":"CAPEX / investimento inicial","incorporation":"Constituição EAS","invoice":"Certificado de faturação eletrônica","seal":"Selo societário","office_setup":"Mobiliário/escritório inicial","office_life":"Vida útil mobiliário/escritório","computers":"Quantidade de computadores","computer_unit":"Custo unitário do computador","computer_life":"Vida útil computadores","deduct":"Deduzir gastos de abertura no ano 1 para base do IRE","depreciate":"Aplicar depreciação fiscal de ativos fixos",
"taxes":"Impostos Paraguai e IVA crédito","ire":"IRE","idu_resident_rate":"IDU residente","idu_nonresident_rate":"IDU não residente","idu_status":"Tratamento IDU dos sócios","idu_resident":"Sócios residentes fiscais no Paraguai","idu_nonresident":"Sócios não residentes fiscais no Paraguai","distribution":"% de lucro distribuído","vat_general":"IVA crédito gastos gerais","vat_rent":"IVA crédito aluguel","calc_vat":"Calcular IVA crédito fiscal",
"inflation":"Atualização temporal de custos","inflation_py":"Inflação/reajuste anual dos custos","opex_title":"O que inclui OPEX?","opex_text":"OPEX são gastos operacionais recorrentes. Inclui salários, prestadores paraguaios, prestadores brasileiros, aluguel, contabilidade, assessorias, energia, internet, telefonia, seguros, software e bens de consumo. Prestadores brasileiros entram como custo direto, não geram IVA crédito no Paraguai e reduzem EBITDA, margem bruta e base do IRE.",
"capex_text":"CAPEX é a saída inicial de caixa: constituição, certificados, selo, mobiliário e equipamentos. Para IRE, o modelo separa gastos de abertura dedutíveis e depreciação fiscal dos ativos fixos.","vat_text":"Como exportação de serviços, não se calcula IVA débito sobre receitas. O IVA crédito é estimado sobre serviços/fornecedores paraguaios gravados, bens de consumo e aluguel. Prestadores brasileiros não geram IVA crédito neste modelo.","idu_text":"Dividendos/lucros distribuídos pela EAS são tratados como IDU. Use 8% se o beneficiário for residente fiscal paraguaio e 15% se for não residente. Residência temporária migratória não equivale automaticamente à residência fiscal.",
"k_revenue":"Receita acumulada","k_opex":"OPEX acumulado","k_ebitda":"EBITDA acumulado","k_net":"Resultado líquido acumulado","k_cash":"Fluxo acumulado","k_gm":"Margem bruta média","k_nm":"Margem líquida média","k_vat":"IVA crédito acumulado","evolution":"Evolução temporal de receita, OPEX, EBITDA e resultado líquido","margins":"Evolução das margens","costs":"Estrutura de gastos e investimento","tax_chart":"Deduções fiscais, IRE, IDU e IVA crédito","cash_chart":"Fluxo de caixa líquido e fluxo acumulado","summary_title":"Quadro geral por grandes rubros","summary_text":"Resumo anual de receita, OPEX, CAPEX, impostos, resultado líquido e fluxo acumulado.","detail_title":"Quadro detalhado por conta","detail_text":"Detalhamento anual de OPEX, CAPEX, deduções fiscais, impostos e IVA crédito.","model_title":"Tabela completa do modelo","download":"Baixar CSV do cenário","year":"Ano","concept":"Conceito","account":"Conta","level1":"Rubro nível 1","level2":"Rubro nível 2"},
"ES": {
"app_title":"Análisis financiero: operación en Paraguay","subtitle":"Modelo editable para proyectar ingresos, costos, impuestos, EBITDA, márgenes y flujo de caja de la operación paraguaya.",
"note":"Nota: validar el encuadre fiscal final con contador/abogado tributario, especialmente IVA crédito de exportadores, residencia fiscal de los socios, precios de transferencia y retenciones aplicables.",
"settings":"Calculadora de supuestos","guide":"Guía de lectura del modelo","time_currency":"Horizonte temporal, idioma y moneda","language":"Idioma","currency":"Moneda de presentación","years":"Años de proyección",
"income_fx":"Ingresos y tipo de cambio","annual_revenue":"Facturación anual inicial","revenue_growth":"Crecimiento anual de ingresos","pyg_per_brl":"PYG por BRL","pyg_per_usd":"PYG por USD",
"personal":"Servicios personales","employees":"Funcionarios","salary":"Salario mensual por funcionario","py_contractors":"Prestadores PJ en Paraguay","py_fee":"Fee mensual PJ Paraguay","br_providers":"Prestadores de servicios brasileros","br_fee":"Remuneración media mensual por prestador brasilero","ips":"IPS patronal","use_payroll":"Incluir aguinaldo e IPS para funcionarios en relación de dependencia",
"non_personal":"Servicios no personales y costos operativos","rent":"Alquiler mensual de oficina","accounting":"Contabilidad mensual","advisory":"Asesorías anuales","regulatory":"Costos regulatorios anuales","utilities":"Electricidad/servicios mensuales","internet":"Internet mensual","phone":"Telefonía mensual","insurance":"Seguros anuales","supplies":"Librería/papelería mensual","software":"Software mensual",
"capex":"CAPEX / inversión inicial","incorporation":"Constitución EAS","invoice":"Certificado de facturación electrónica","seal":"Sello societario","office_setup":"Mobiliario/oficina inicial","office_life":"Vida útil mobiliario/oficina","computers":"Cantidad de computadoras","computer_unit":"Costo unitario computadora","computer_life":"Vida útil computadoras","deduct":"Deducir gastos de apertura en el año 1 para base IRE","depreciate":"Aplicar depreciación fiscal de activos fijos",
"taxes":"Impuestos Paraguay e IVA crédito","ire":"IRE","idu_resident_rate":"IDU residente","idu_nonresident_rate":"IDU no residente","idu_status":"Tratamiento IDU de los socios","idu_resident":"Socios residentes fiscales en Paraguay","idu_nonresident":"Socios no residentes fiscales en Paraguay","distribution":"% utilidad distribuida","vat_general":"IVA crédito gastos generales","vat_rent":"IVA crédito alquiler","calc_vat":"Calcular IVA crédito fiscal",
"inflation":"Actualización temporal de costos","inflation_py":"Inflación/reajuste anual de costos","opex_title":"¿Qué incluye OPEX?","opex_text":"OPEX son gastos operativos recurrentes. Incluye salarios, prestadores paraguayos, prestadores brasileros, alquiler, contabilidad, asesorías, electricidad, internet, telefonía, seguros, software y bienes de consumo. Los prestadores brasileros entran como costo directo, no generan IVA crédito en Paraguay y reducen EBITDA, margen bruto y base del IRE.",
"capex_text":"CAPEX es la salida inicial de caja: constitución, certificados, sello, mobiliario y equipos. Para IRE, el modelo separa gastos de apertura deducibles y depreciación fiscal de activos fijos.","vat_text":"Como exportación de servicios, no se calcula IVA débito sobre ingresos. El IVA crédito se estima sobre servicios/proveedores paraguayos gravados, bienes de consumo y alquiler. Los prestadores brasileros no generan IVA crédito en este modelo.","idu_text":"Dividendos/utilidades distribuidos por la EAS se tratan como IDU. Use 8% si el beneficiario es residente fiscal paraguayo y 15% si es no residente. La residencia temporal migratoria no equivale automáticamente a residencia fiscal.",
"k_revenue":"Ingresos acumulados","k_opex":"OPEX acumulado","k_ebitda":"EBITDA acumulado","k_net":"Resultado neto acumulado","k_cash":"Flujo acumulado","k_gm":"Margen bruto promedio","k_nm":"Margen neto promedio","k_vat":"IVA crédito acumulado","evolution":"Evolución temporal de ingresos, OPEX, EBITDA y resultado neto","margins":"Evolución de márgenes","costs":"Estructura de egresos e inversión","tax_chart":"Deducciones fiscales, IRE, IDU e IVA crédito","cash_chart":"Flujo de caja neto y flujo acumulado","summary_title":"Cuadro general por grandes rubros","summary_text":"Resumen anual de ingresos, OPEX, CAPEX, impuestos, resultado neto y flujo acumulado.","detail_title":"Cuadro detallado por cuenta","detail_text":"Detalle anual de OPEX, CAPEX, deducciones fiscales, impuestos e IVA crédito.","model_title":"Tabla completa del modelo","download":"Descargar CSV del escenario","year":"Año","concept":"Concepto","account":"Cuenta","level1":"Rubro nivel 1","level2":"Rubro nivel 2"}
}

def t(lang, key): return TEXT.get(lang or "PT", TEXT["PT"]).get(key, key)
def brl_from_pyg(x, rate): return 0 if rate <= 0 else x / rate
def brl_from_usd(x, usd_rate, brl_rate): return brl_from_pyg(x * usd_rate, brl_rate)
def to_currency(x_brl, currency, pyg_per_brl): return x_brl * pyg_per_brl if currency == "PYG" else x_brl
def money(x_brl, currency, pyg_per_brl):
    prefix = "Gs." if currency == "PYG" else "R$"
    return f"{prefix} {to_currency(x_brl, currency, pyg_per_brl):,.0f}".replace(",", ".")
def pct(x): return f"{x*100:.1f}%"
def sdiv(a,b): return a/b if b else 0

def compute_model(p):
    rows, detail = [], []
    inc = brl_from_usd(p["incorporation_usd"], p["pyg_per_usd"], p["pyg_per_brl"])
    cert = brl_from_pyg(p["invoice_cert_pyg"], p["pyg_per_brl"])
    seal = brl_from_pyg(p["seal_pyg"], p["pyg_per_brl"])
    startup = inc + cert + seal
    office = brl_from_pyg(p["office_setup_pyg"], p["pyg_per_brl"])
    computers = brl_from_pyg(p["computer_count"] * p["computer_unit_pyg"], p["pyg_per_brl"])
    capex_total = startup + office + computers
    office_dep = office / max(1, int(p["office_setup_life_years"]))
    comp_dep = computers / max(1, int(p["computer_life_years"]))
    for y in range(1, max(1, int(p["years"])) + 1):
        f = (1 + p["inflation_py"]) ** (y-1)
        rev = p["annual_revenue_brl"] * ((1 + p["revenue_growth"]) ** (y-1))
        sal = brl_from_pyg(p["employee_count"] * p["monthly_salary_pyg"] * 12 * f, p["pyg_per_brl"])
        py_pj = brl_from_pyg(p["contractor_count"] * p["monthly_contractor_fee_pyg"] * 12 * f, p["pyg_per_brl"])
        br_pj = p["brazilian_provider_count"] * p["monthly_brazilian_provider_fee_brl"] * 12 * f
        aguinaldo = sal * p["aguinaldo_rate"] if p["use_payroll"] else 0
        ips = sal * p["ips_employer"] if p["use_payroll"] else 0
        rent = brl_from_pyg(p["monthly_office_rent_pyg"] * 12 * f, p["pyg_per_brl"])
        acc = brl_from_pyg(p["accounting_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        adv = brl_from_pyg(p["advisory_annual_pyg"] * f, p["pyg_per_brl"])
        reg = brl_from_pyg(p["regulatory_annual_pyg"] * f, p["pyg_per_brl"])
        util = brl_from_pyg(p["utilities_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        internet = brl_from_pyg(p["internet_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        phone = brl_from_pyg(p["phone_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        ins = brl_from_pyg(p["insurance_annual_pyg"] * f, p["pyg_per_brl"])
        software = brl_from_pyg(p["software_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        supplies = brl_from_pyg(p["supplies_monthly_pyg"] * 12 * f, p["pyg_per_brl"])
        personal = sal + py_pj + br_pj + aguinaldo + ips
        non_personal = rent + acc + adv + reg + util + internet + phone + ins + software
        opex = personal + non_personal + supplies
        vat_base = py_pj + acc + adv + reg + util + internet + phone + ins + software + supplies
        vat_general = vat_base * p["expense_vat_general"] if p["calculate_vat_credit"] else 0
        vat_rent = rent * p["rent_vat"] if p["calculate_vat_credit"] else 0
        vat_credit = vat_general + vat_rent
        gross = rev - (personal + software)
        ebitda = rev - opex
        startup_ded = startup if y == 1 and p["deduct_startup_expenses_year1"] else 0
        dep = (office_dep if p["depreciate_fixed_assets"] and y <= p["office_setup_life_years"] else 0) + (comp_dep if p["depreciate_fixed_assets"] and y <= p["computer_life_years"] else 0)
        base_ire = ebitda - startup_ded - dep
        ire = max(0, base_ire * p["ire_rate"])
        fiscal_after_ire = max(0, base_ire - ire)
        idu_rate = p["idu_rate_resident"] if p["idu_residency_status"] == "resident" else p["idu_rate_nonresident"]
        idu = max(0, fiscal_after_ire * p["dividend_distribution_rate"] * idu_rate)
        net = fiscal_after_ire - idu
        capex_cash = capex_total if y == 1 else 0
        cash = ebitda - ire - idu - capex_cash
        row = {"Año": y, "Ano": y, "Ingresos BRL": rev, "Receita BRL": rev, "Salarios BRL": sal, "Salários BRL": sal, "Prestadores PJ Paraguay BRL": py_pj, "Prestadores PJ Paraguai BRL": py_pj, "Prestadores brasileros BRL": br_pj, "Prestadores brasileiros BRL": br_pj, "Aguinaldo / 13º BRL": aguinaldo, "IPS patronal BRL": ips, "Alquiler oficina BRL": rent, "Aluguel escritório BRL": rent, "Contabilidad BRL": acc, "Contabilidade BRL": acc, "Asesorías BRL": adv, "Assessorias BRL": adv, "Regulatorios BRL": reg, "Regulatórios BRL": reg, "Electricidad/servicios BRL": util, "Energia/serviços BRL": util, "Internet BRL": internet, "Telefonía BRL": phone, "Telefonia BRL": phone, "Seguros BRL": ins, "Software BRL": software, "Librería/papelería BRL": supplies, "Papelaria/consumo BRL": supplies, "Servicios personales BRL": personal, "Serviços pessoais BRL": personal, "Servicios no personales BRL": non_personal, "Serviços não pessoais BRL": non_personal, "Bienes consumo e insumos BRL": supplies, "Bens de consumo e insumos BRL": supplies, "OPEX BRL": opex, "CAPEX caja BRL": capex_cash, "CAPEX caixa BRL": capex_cash, "IVA crédito fiscal BRL": vat_credit, "IVA crédito general BRL": vat_general, "IVA crédito aluguel BRL": vat_rent, "Resultado bruto BRL": gross, "Lucro bruto BRL": gross, "Margen bruto": sdiv(gross, rev), "Margem bruta": sdiv(gross, rev), "EBITDA BRL": ebitda, "Margen EBITDA": sdiv(ebitda, rev), "Margem EBITDA": sdiv(ebitda, rev), "Gastos apertura deducibles IRE BRL": startup_ded, "Gastos de abertura dedutíveis IRE BRL": startup_ded, "Depreciación fiscal BRL": dep, "Depreciação fiscal BRL": dep, "Base IRE BRL": base_ire, "IRE BRL": ire, "Resultado después de IRE BRL": fiscal_after_ire, "Resultado após IRE BRL": fiscal_after_ire, "IDU BRL": idu, "Resultado neto remitible BRL": net, "Resultado líquido remetível BRL": net, "Margen neto": sdiv(net, rev), "Margem líquida": sdiv(net, rev), "Flujo de caja neto BRL": cash, "Fluxo de caixa líquido BRL": cash}
        capex_items = {"Constitución EAS BRL": inc if y==1 else 0, "Certificado facturación electrónica BRL": cert if y==1 else 0, "Sello societario BRL": seal if y==1 else 0, "Mobiliario/oficina inicial BRL": office if y==1 else 0, "Equipos informáticos BRL": computers if y==1 else 0, "Constituição EAS BRL": inc if y==1 else 0, "Certificado faturação eletrônica BRL": cert if y==1 else 0, "Selo societário BRL": seal if y==1 else 0, "Mobiliário/escritório inicial BRL": office if y==1 else 0, "Equipamentos informáticos BRL": computers if y==1 else 0}
        row.update(capex_items)
        rows.append(row)
        details = [("OPEX","Servicios personales","Salarios","OPEX","Serviços pessoais","Salários",sal),("OPEX","Servicios personales","Prestadores PJ Paraguay","OPEX","Serviços pessoais","Prestadores PJ Paraguai",py_pj),("OPEX","Servicios personales","Prestadores brasileros","OPEX","Serviços pessoais","Prestadores brasileiros",br_pj),("OPEX","Servicios personales","Aguinaldo / 13º","OPEX","Serviços pessoais","Aguinaldo / 13º",aguinaldo),("OPEX","Servicios personales","IPS patronal","OPEX","Serviços pessoais","IPS patronal",ips),("OPEX","Servicios no personales","Alquiler oficina","OPEX","Serviços não pessoais","Aluguel escritório",rent),("OPEX","Servicios no personales","Contabilidad","OPEX","Serviços não pessoais","Contabilidade",acc),("OPEX","Servicios no personales","Asesorías","OPEX","Serviços não pessoais","Assessorias",adv),("OPEX","Servicios no personales","Regulatorios","OPEX","Serviços não pessoais","Regulatórios",reg),("OPEX","Servicios no personales","Electricidad/servicios","OPEX","Serviços não pessoais","Energia/serviços",util),("OPEX","Servicios no personales","Internet","OPEX","Serviços não pessoais","Internet",internet),("OPEX","Servicios no personales","Telefonía","OPEX","Serviços não pessoais","Telefonia",phone),("OPEX","Servicios no personales","Seguros","OPEX","Serviços não pessoais","Seguros",ins),("OPEX","Servicios no personales","Software","OPEX","Serviços não pessoais","Software",software),("OPEX","Bienes de consumo e insumos","Librería/papelería","OPEX","Bens de consumo e insumos","Papelaria/consumo",supplies),("Deducciones fiscales","Gastos de apertura","Gastos deducibles de apertura","Deduções fiscais","Gastos de abertura","Gastos dedutíveis de abertura",startup_ded),("Deducciones fiscales","Depreciación fiscal","Depreciación activos fijos","Deduções fiscais","Depreciação fiscal","Depreciação ativos fixos",dep),("Impuestos","IRE","IRE","Impostos","IRE","IRE",ire),("Impuestos","IDU","IDU","Impostos","IDU","IDU",idu),("IVA crédito fiscal","IVA crédito","IVA crédito general","IVA crédito fiscal","IVA crédito","IVA crédito geral",vat_general),("IVA crédito fiscal","IVA crédito","IVA crédito alquiler","IVA crédito fiscal","IVA crédito","IVA crédito aluguel",vat_rent),("CAPEX caja","Apertura e inversión inicial","Constitución EAS","CAPEX caixa","Gastos de abertura","Constituição EAS",inc if y==1 else 0),("CAPEX caja","Apertura e inversión inicial","Certificado facturación electrónica","CAPEX caixa","Gastos de abertura","Certificado faturação eletrônica",cert if y==1 else 0),("CAPEX caja","Apertura e inversión inicial","Sello societario","CAPEX caixa","Gastos de abertura","Selo societário",seal if y==1 else 0),("CAPEX caja","Activos fijos","Mobiliario/oficina inicial","CAPEX caixa","Ativos fixos","Mobiliário/escritório inicial",office if y==1 else 0),("CAPEX caja","Activos fijos","Equipos informáticos","CAPEX caixa","Ativos fixos","Equipamentos informáticos",computers if y==1 else 0)]
        for r1es,r2es,ces,r1pt,r2pt,cpt,val in details:
            detail.append({"Año":y,"Ano":y,"Rubro nivel 1":r1es,"Rubro nivel 2":r2es,"Cuenta":ces,"Rubro nível 1":r1pt,"Rubro nível 2":r2pt,"Conta":cpt,"Valor BRL":val})
    df = pd.DataFrame(rows)
    df["Flujo acumulado BRL"] = df["Flujo de caja neto BRL"].cumsum()
    df["Fluxo acumulado BRL"] = df["Fluxo de caixa líquido BRL"].cumsum()
    return df, pd.DataFrame(detail)

def inp(key, id_, value, step=1, min_=0, suffix=None):
    return dbc.Col([dbc.Label(html.Span(id={"type":"i18n","key":key}), className="small fw-semibold"), dbc.InputGroup([dbc.Input(id=id_, type="number", value=value, step=step, min=min_), dbc.InputGroupText(suffix) if suffix else html.Span()])], md=3, sm=6, xs=12, className="mb-3")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server
app.layout = html.Div([html.Header(dbc.Container([dbc.Row([dbc.Col([html.H1(id={"type":"i18n","key":"app_title"}, className="m-0", style={"fontFamily":"Avenir, Arial, sans-serif","fontWeight":"700","fontSize":"2rem","color":"#333"}), html.P(id={"type":"i18n","key":"subtitle"}, className="text-muted mb-0")], md=10)], justify="center", className="py-4")]), style={"backgroundColor":"white","borderBottom":"1px solid #eee"}), dbc.Container([dbc.Alert(id={"type":"i18n","key":"note"}, color="warning", className="mt-3"), dbc.Card([dbc.CardHeader(html.H5(id={"type":"i18n","key":"guide"}, className="m-0")), dbc.CardBody(dbc.Accordion([dbc.AccordionItem(html.P(id={"type":"i18n","key":"opex_text"}), title="OPEX"), dbc.AccordionItem(html.P(id={"type":"i18n","key":"capex_text"}), title="CAPEX"), dbc.AccordionItem(html.P(id={"type":"i18n","key":"vat_text"}), title="IVA"), dbc.AccordionItem(html.P(id={"type":"i18n","key":"idu_text"}), title="IDU / IRP")], start_collapsed=True))], className="shadow-sm mb-4"), dbc.Card([dbc.CardHeader(html.H5(id={"type":"i18n","key":"settings"}, className="m-0")), dbc.CardBody([html.H6(id={"type":"i18n","key":"time_currency"}), dbc.Row([dbc.Col([dbc.Label(html.Span(id={"type":"i18n","key":"language"}), className="small fw-semibold"), dbc.RadioItems(id="language", options=[{"label":"Português","value":"PT"},{"label":"Español","value":"ES"}], value="PT", inline=True)], md=4), dbc.Col([dbc.Label(html.Span(id={"type":"i18n","key":"currency"}), className="small fw-semibold"), dbc.RadioItems(id="display_currency", options=[{"label":"BRL","value":"BRL"},{"label":"PYG","value":"PYG"}], value="BRL", inline=True)], md=4), dbc.Col([dbc.Label(html.Span(id={"type":"i18n","key":"years"}), className="small fw-semibold"), dcc.Slider(id="years", min=1, max=20, step=1, value=10, marks={i:str(i) for i in range(1,21)}, tooltip={"placement":"bottom","always_visible":True})], md=4)]), html.Hr(), html.H6(id={"type":"i18n","key":"income_fx"}), dbc.Row([inp("annual_revenue","annual_revenue_brl",DEFAULTS["annual_revenue_brl"],100000,0,"BRL"), inp("revenue_growth","revenue_growth",DEFAULTS["revenue_growth"]*100,0.5,-100,"%"), inp("pyg_per_brl","pyg_per_brl",DEFAULTS["pyg_per_brl"],10,1), inp("pyg_per_usd","pyg_per_usd",DEFAULTS["pyg_per_usd"],10,1)]), html.Hr(), html.H6(id={"type":"i18n","key":"personal"}), dbc.Row([inp("employees","employee_count",DEFAULTS["employee_count"],1,0), inp("salary","monthly_salary_pyg",DEFAULTS["monthly_salary_pyg"],100000,0,"PYG"), inp("py_contractors","contractor_count",DEFAULTS["contractor_count"],1,0), inp("py_fee","monthly_contractor_fee_pyg",DEFAULTS["monthly_contractor_fee_pyg"],100000,0,"PYG"), inp("br_providers","brazilian_provider_count",0,1,0), inp("br_fee","monthly_brazilian_provider_fee_brl",8000,100,0,"BRL"), inp("ips","ips_employer",DEFAULTS["ips_employer"]*100,0.1,0,"%")]), dbc.Checklist(id="use_payroll", options=[{"label":"","value":1}], value=[1], switch=True), html.Hr(), html.H6(id={"type":"i18n","key":"non_personal"}), dbc.Row([inp("rent","monthly_office_rent_pyg",DEFAULTS["monthly_office_rent_pyg"],100000,0,"PYG"), inp("accounting","accounting_monthly_pyg",DEFAULTS["accounting_monthly_pyg"],100000,0,"PYG"), inp("advisory","advisory_annual_pyg",DEFAULTS["advisory_annual_pyg"],100000,0,"PYG"), inp("regulatory","regulatory_annual_pyg",DEFAULTS["regulatory_annual_pyg"],100000,0,"PYG"), inp("utilities","utilities_monthly_pyg",DEFAULTS["utilities_monthly_pyg"],50000,0,"PYG"), inp("internet","internet_monthly_pyg",DEFAULTS["internet_monthly_pyg"],50000,0,"PYG"), inp("phone","phone_monthly_pyg",DEFAULTS["phone_monthly_pyg"],50000,0,"PYG"), inp("insurance","insurance_annual_pyg",DEFAULTS["insurance_annual_pyg"],100000,0,"PYG"), inp("supplies","supplies_monthly_pyg",DEFAULTS["supplies_monthly_pyg"],50000,0,"PYG"), inp("software","software_monthly_pyg",DEFAULTS["software_monthly_pyg"],100000,0,"PYG")]), html.Hr(), html.H6(id={"type":"i18n","key":"capex"}), dbc.Row([inp("incorporation","incorporation_usd",400,10,0,"USD"), inp("invoice","invoice_cert_pyg",480000,10000,0,"PYG"), inp("seal","seal_pyg",130000,10000,0,"PYG"), inp("office_setup","office_setup_pyg",10000000,100000,0,"PYG"), inp("office_life","office_setup_life_years",5,1,1), inp("computers","computer_count",4,1,0), inp("computer_unit","computer_unit_pyg",3000000,100000,0,"PYG"), inp("computer_life","computer_life_years",4,1,1)]), dbc.Checklist(id="capex_tax_options", options=[{"label":"","value":"deduct"},{"label":"","value":"depreciate"}], value=["deduct","depreciate"], switch=True), html.Hr(), html.H6(id={"type":"i18n","key":"taxes"}), dbc.Row([inp("ire","ire_rate",10,0.1,0,"%"), inp("idu_resident_rate","idu_rate_resident",8,0.1,0,"%"), inp("idu_nonresident_rate","idu_rate_nonresident",15,0.1,0,"%"), inp("distribution","dividend_distribution_rate",100,1,0,"%"), inp("vat_general","expense_vat_general",10,0.1,0,"%"), inp("vat_rent","rent_vat",10,0.1,0,"%")]), dbc.Row([dbc.Col([dbc.Label(html.Span(id={"type":"i18n","key":"idu_status"}), className="small fw-semibold"), dbc.RadioItems(id="idu_residency_status", options=[{"label":"Residente","value":"resident"},{"label":"Não residente","value":"nonresident"}], value="nonresident")], md=6), dbc.Col(dbc.Checklist(id="calculate_vat_credit", options=[{"label":"","value":1}], value=[1], switch=True), md=6)]), html.Hr(), html.H6(id={"type":"i18n","key":"inflation"}), dbc.Row([inp("inflation_py","inflation_py",4,0.5,0,"%")])])], className="shadow-sm mb-4"), dbc.Row(id="kpi_cards", className="g-3 mb-4"), dbc.Row([dbc.Col(dcc.Graph(id="evolution_chart"), md=8), dbc.Col(dcc.Graph(id="margin_chart"), md=4)]), dbc.Row([dbc.Col(dcc.Graph(id="cost_chart"), md=6), dbc.Col(dcc.Graph(id="tax_chart"), md=6)]), dbc.Row([dbc.Col(dcc.Graph(id="cash_chart"), md=12)]), html.H4(id={"type":"i18n","key":"summary_title"}, className="mt-4"), html.P(id={"type":"i18n","key":"summary_text"}, className="text-muted"), dash_table.DataTable(id="summary_table", page_size=25, sort_action="native", filter_action="native", style_table={"overflowX":"auto"}, style_cell={"fontFamily":"Arial","fontSize":"13px","padding":"8px"}, style_header={"fontWeight":"bold","backgroundColor":"#f8f9fa"}), html.H4(id={"type":"i18n","key":"detail_title"}, className="mt-4"), html.P(id={"type":"i18n","key":"detail_text"}, className="text-muted"), dash_table.DataTable(id="detail_table", page_size=25, sort_action="native", filter_action="native", style_table={"overflowX":"auto"}, style_cell={"fontFamily":"Arial","fontSize":"13px","padding":"8px"}, style_header={"fontWeight":"bold","backgroundColor":"#f8f9fa"}), html.H4(id={"type":"i18n","key":"model_title"}, className="mt-4"), dash_table.DataTable(id="model_table", page_size=10, sort_action="native", filter_action="native", style_table={"overflowX":"auto"}, style_cell={"fontFamily":"Arial","fontSize":"13px","padding":"8px"}, style_header={"fontWeight":"bold","backgroundColor":"#f8f9fa"}), dcc.Download(id="download_model"), dbc.Button(id="download_btn", color="primary", className="my-3")], fluid=True)], style={"backgroundColor":"#f7f8fa","minHeight":"100vh"})

@app.callback(Output({"type":"i18n","key":ALL},"children"), Output("use_payroll","options"), Output("capex_tax_options","options"), Output("calculate_vat_credit","options"), Output("idu_residency_status","options"), Output("download_btn","children"), Input("language","value"), State({"type":"i18n","key":ALL},"id"))
def update_text(lang, ids):
    lang = lang or "PT"
    return [t(lang, i["key"]) for i in ids], [{"label":t(lang,"use_payroll"),"value":1}], [{"label":t(lang,"deduct"),"value":"deduct"},{"label":t(lang,"depreciate"),"value":"depreciate"}], [{"label":t(lang,"calc_vat"),"value":1}], [{"label":t(lang,"idu_resident"),"value":"resident"},{"label":t(lang,"idu_nonresident"),"value":"nonresident"}], t(lang,"download")

def collect(vals):
    keys=["years","display_currency","language","annual_revenue_brl","revenue_growth","pyg_per_brl","pyg_per_usd","employee_count","monthly_salary_pyg","contractor_count","monthly_contractor_fee_pyg","brazilian_provider_count","monthly_brazilian_provider_fee_brl","ips_employer","use_payroll","monthly_office_rent_pyg","accounting_monthly_pyg","advisory_annual_pyg","regulatory_annual_pyg","utilities_monthly_pyg","internet_monthly_pyg","phone_monthly_pyg","insurance_annual_pyg","supplies_monthly_pyg","software_monthly_pyg","incorporation_usd","invoice_cert_pyg","seal_pyg","office_setup_pyg","office_setup_life_years","computer_count","computer_unit_pyg","computer_life_years","capex_tax_options","ire_rate","idu_rate_resident","idu_rate_nonresident","idu_residency_status","dividend_distribution_rate","expense_vat_general","rent_vat","calculate_vat_credit","inflation_py"]
    p=DEFAULTS.copy()
    for k,v in zip(keys,vals):
        if k in ["use_payroll","calculate_vat_credit"]: p[k]=bool(v)
        elif k=="capex_tax_options": p["deduct_startup_expenses_year1"]="deduct" in (v or []); p["depreciate_fixed_assets"]="depreciate" in (v or [])
        elif k in ["display_currency","language","idu_residency_status"]: p[k]=v or DEFAULTS[k]
        elif k in ["revenue_growth","ips_employer","ire_rate","idu_rate_resident","idu_rate_nonresident","dividend_distribution_rate","expense_vat_general","rent_vat","inflation_py"]: p[k]=(v or 0)/100
        elif k in ["years","employee_count","contractor_count","brazilian_provider_count","computer_count","office_setup_life_years","computer_life_years"]: p[k]=max(0,int(v or 0))
        else: p[k]=v or 0
    p["years"]=max(1,p["years"]); p["office_setup_life_years"]=max(1,p["office_setup_life_years"]); p["computer_life_years"]=max(1,p["computer_life_years"])
    return p

inputs=[Input(i,"value") for i in ["years","display_currency","language","annual_revenue_brl","revenue_growth","pyg_per_brl","pyg_per_usd","employee_count","monthly_salary_pyg","contractor_count","monthly_contractor_fee_pyg","brazilian_provider_count","monthly_brazilian_provider_fee_brl","ips_employer","use_payroll","monthly_office_rent_pyg","accounting_monthly_pyg","advisory_annual_pyg","regulatory_annual_pyg","utilities_monthly_pyg","internet_monthly_pyg","phone_monthly_pyg","insurance_annual_pyg","supplies_monthly_pyg","software_monthly_pyg","incorporation_usd","invoice_cert_pyg","seal_pyg","office_setup_pyg","office_setup_life_years","computer_count","computer_unit_pyg","computer_life_years","capex_tax_options","ire_rate","idu_rate_resident","idu_rate_nonresident","idu_residency_status","dividend_distribution_rate","expense_vat_general","rent_vat","calculate_vat_credit","inflation_py"]]

@app.callback(Output("kpi_cards","children"),Output("evolution_chart","figure"),Output("margin_chart","figure"),Output("cost_chart","figure"),Output("tax_chart","figure"),Output("cash_chart","figure"),Output("summary_table","data"),Output("summary_table","columns"),Output("detail_table","data"),Output("detail_table","columns"),Output("model_table","data"),Output("model_table","columns"),*inputs)
def update(*vals):
    p=collect(vals); lang=p["language"]; cur=p["display_currency"]; pref="Gs. " if cur=="PYG" else "R$ "
    df,det=compute_model(p); year="Ano" if lang=="PT" else "Año"; concept=t(lang,"concept")
    rev="Receita BRL" if lang=="PT" else "Ingresos BRL"; net="Resultado líquido remetível BRL" if lang=="PT" else "Resultado neto remitible BRL"; cash="Fluxo acumulado BRL" if lang=="PT" else "Flujo acumulado BRL"; gm="Margem bruta" if lang=="PT" else "Margen bruto"; nm="Margem líquida" if lang=="PT" else "Margen neto"
    def k(c): return df[c].sum()
    cards=[dbc.Col(dbc.Card(dbc.CardBody([html.Div(t(lang,a),className="text-muted small"),html.H3(b,className="mb-1"),html.Div(c,className="small text-muted")]),className="shadow-sm border-0"),md=3,sm=6) for a,b,c in [("k_revenue",money(k(rev),cur,p["pyg_per_brl"]),""),("k_opex",money(k("OPEX BRL"),cur,p["pyg_per_brl"]),""),("k_ebitda",money(k("EBITDA BRL"),cur,p["pyg_per_brl"]),""),("k_net",money(k(net),cur,p["pyg_per_brl"]),""),("k_cash",money(df[cash].iloc[-1],cur,p["pyg_per_brl"]),""),("k_gm",pct(df[gm].mean()),""),("k_nm",pct(df[nm].mean()),""),("k_vat",money(k("IVA crédito fiscal BRL"),cur,p["pyg_per_brl"]),"")]]
    ev=pd.DataFrame({year:df[year], t(lang,"k_revenue"):df[rev].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])), "OPEX":df["OPEX BRL"].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])), "EBITDA":df["EBITDA BRL"].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])), t(lang,"k_net"):df[net].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"]))})
    fig_ev=px.line(ev.melt(id_vars=year,var_name=concept,value_name=cur),x=year,y=cur,color=concept,markers=True,template="plotly_white",title=t(lang,"evolution")); fig_ev.update_layout(yaxis_tickprefix=pref,legend_title_text="")
    margin_cols=["Margem bruta","Margem EBITDA","Margem líquida"] if lang=="PT" else ["Margen bruto","Margen EBITDA","Margen neto"]
    fig_m=px.line(df.melt(id_vars=year,value_vars=margin_cols,var_name="Indicador",value_name="%"),x=year,y="%",color="Indicador",markers=True,template="plotly_white",title=t(lang,"margins")); fig_m.update_layout(yaxis_tickformat=".1%",legend_title_text="")
    costs={"Serviços pessoais" if lang=="PT" else "Servicios personales":"Serviços pessoais BRL" if lang=="PT" else "Servicios personales BRL","Serviços não pessoais" if lang=="PT" else "Servicios no personales":"Serviços não pessoais BRL" if lang=="PT" else "Servicios no personales BRL","CAPEX":"CAPEX caixa BRL" if lang=="PT" else "CAPEX caja BRL"}
    cdf=pd.DataFrame({year:df[year], **{lab:df[col].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])) for lab,col in costs.items()}})
    fig_c=px.area(cdf.melt(id_vars=year,var_name="Rubro",value_name=cur),x=year,y=cur,color="Rubro",template="plotly_white",title=t(lang,"costs")); fig_c.update_layout(yaxis_tickprefix=pref,legend_title_text="")
    tax_cols={"Base IRE":"Base IRE BRL","IRE":"IRE BRL","IDU":"IDU BRL","IVA crédito":"IVA crédito fiscal BRL"}
    tdf=pd.DataFrame({year:df[year], **{lab:df[col].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])) for lab,col in tax_cols.items()}})
    fig_t=px.bar(tdf.melt(id_vars=year,var_name=concept,value_name=cur),x=year,y=cur,color=concept,barmode="group",template="plotly_white",title=t(lang,"tax_chart")); fig_t.update_layout(yaxis_tickprefix=pref,legend_title_text="")
    cash_col="Fluxo de caixa líquido BRL" if lang=="PT" else "Flujo de caja neto BRL"
    acc_col="Fluxo acumulado BRL" if lang=="PT" else "Flujo acumulado BRL"
    fdf=pd.DataFrame({year:df[year],"Fluxo" if lang=="PT" else "Flujo":df[cash_col].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"])),"Acumulado":df[acc_col].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"]))})
    fig_f=px.line(fdf.melt(id_vars=year,var_name=concept,value_name=cur),x=year,y=cur,color=concept,markers=True,template="plotly_white",title=t(lang,"cash_chart")); fig_f.update_layout(yaxis_tickprefix=pref,legend_title_text="")
    summap=[(t(lang,"k_revenue"),rev),("OPEX","OPEX BRL"),("EBITDA","EBITDA BRL"),("Base IRE","Base IRE BRL"),("IRE","IRE BRL"),("IDU","IDU BRL"),(t(lang,"k_net"),net),("CAPEX","CAPEX caixa BRL" if lang=="PT" else "CAPEX caja BRL"),(t(lang,"k_cash"),acc_col),("IVA crédito","IVA crédito fiscal BRL"),(t(lang,"k_gm"),gm),(t(lang,"k_nm"),nm)]
    srows=[]
    for label,col in summap:
        row={concept:label}; is_pct=col in [gm,nm]
        for _,r in df.iterrows(): row[f"{t(lang,'year')} {int(r[year])}"] = (f"{r[col]*100:.2f}%" if is_pct else int(round(to_currency(r[col],cur,p["pyg_per_brl"]),0)))
        srows.append(row)
    sdf=pd.DataFrame(srows); scols=[{"name":c,"id":c} for c in sdf.columns]
    idx=["Rubro nível 1","Rubro nível 2","Conta"] if lang=="PT" else ["Rubro nivel 1","Rubro nivel 2","Cuenta"]
    mat=det.pivot_table(index=idx, columns=year, values="Valor BRL", aggfunc="sum", fill_value=0).reset_index(); mat.columns=[f"{t(lang,'year')} {int(c)}" if str(c).isdigit() else c for c in mat.columns]
    for col in [c for c in mat.columns if c.startswith(t(lang,'year')+' ')]: mat[col]=mat[col].apply(lambda x:int(round(to_currency(float(x),cur,p["pyg_per_brl"]),0)))
    mcols=[{"name":c,"id":c} for c in mat.columns]
    mdf=df.copy()
    for col in list(mdf.columns):
        if col.endswith(" BRL"):
            mdf[col.replace(" BRL",f" {cur}")]=mdf[col].apply(lambda x:to_currency(x,cur,p["pyg_per_brl"]));
            if cur!="BRL": mdf.drop(columns=[col], inplace=True)
    if lang=="PT": mdf=mdf[[c for c in mdf.columns if not c.startswith("Margen") and c not in ["Año","Ingresos BRL","Resultado neto remitible BRL","Flujo de caja neto BRL","Flujo acumulado BRL"]]]
    else: mdf=mdf[[c for c in mdf.columns if not c.startswith("Margem") and c not in ["Ano","Receita BRL","Resultado líquido remetível BRL","Fluxo de caixa líquido BRL","Fluxo acumulado BRL"]]]
    for col in mdf.columns:
        if col not in ["Año","Ano"] and pd.api.types.is_numeric_dtype(mdf[col]):
            if "Marg" in col: mdf[col]=(mdf[col]*100).round(2).astype(str)+"%"
            else: mdf[col]=mdf[col].round(0).astype(int)
    cols=[{"name":c,"id":c} for c in mdf.columns]
    return cards,fig_ev,fig_m,fig_c,fig_t,fig_f,sdf.to_dict("records"),scols,mat.to_dict("records"),mcols,mdf.to_dict("records"),cols

@app.callback(Output("download_model","data"),Input("download_btn","n_clicks"),*[State(i.component_id,i.component_property) for i in inputs],prevent_initial_call=True)
def download(n,*vals):
    p=collect(vals); df,_=compute_model(p); return dcc.send_data_frame(df.to_csv,f"modelo_operacion_paraguay_{p['language'].lower()}_{p['display_currency'].lower()}.csv",index=False)

if __name__ == "__main__":
    port=int(os.environ.get("PORT",8050)); app.run(host="0.0.0.0",port=port,debug=False)
