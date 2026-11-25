import json
from datetime import date, datetime
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Controle de Combustível",
    page_icon="⛽",
    layout="wide"
)

# Inicialização do estado da sessão (armazenamento ativo por sessão)
if "registros" not in st.session_state:
    st.session_state.registros = []


def formatar_moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_metricas(registros: list) -> dict:
    total = 0.0
    litros = 0.0
    distancia = 0.0
    litros_intervalo = 0.0
    gasto_intervalo = 0.0

    mes_atual = date.today().strftime("%Y-%m")
    gasto_mes = 0.0
    quantidade_mes = 0

    for i, r in enumerate(registros):
        total += r["valor"]
        litros += r["litros"]

        if r["data"].startswith(mes_atual):
            gasto_mes += r["valor"]
            quantidade_mes += 1

        if i > 0:
            anterior = registros[i - 1]
            km_rodados = r["km"] - anterior["km"]
            distancia += km_rodados
            litros_intervalo += r["litros"]
            gasto_intervalo += r["valor"]

    media = (distancia / litros_intervalo) if litros_intervalo > 0 else 0.0
    custo_km = (gasto_intervalo / distancia) if distancia > 0 else 0.0

    return {
        "media": media,
        "total": total,
        "litros": litros,
        "custo_km": custo_km,
        "gasto_mes": gasto_mes,
        "quantidade_mes": quantidade_mes,
    }


# Cabeçalho da aplicação
st.title("⛽ Controle de Combustível")
st.caption("Gestão de abastecimentos, quilometragem e despesas")

metricas = calcular_metricas(st.session_state.registros)

# 1. Cards de indicadores gerais
col1, col2, col3, col4 = st.columns(4)
col1.metric("Consumo médio", f"{formatar_numero(metricas['media'])} km/L" if metricas["media"] else "0 km/L")
col2.metric("Total gasto", formatar_moeda(metricas["total"]))
col3.metric("Total de litros", f"{formatar_numero(metricas['litros'])} L")
col4.metric("Custo por KM", formatar_moeda(metricas["custo_km"]))

st.divider()

# 2. Formulário de novo abastecimento
st.subheader("➕ Novo abastecimento")

with st.form("form_abastecimento", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        data_abast = st.date_input("Data do abastecimento", value=date.today(), format="DD/MM/YYYY")
        valor = st.number_input("Valor gasto (R$)", min_value=0.0, step=0.01, format="%.2f")
    with c2:
        km = st.number_input("Quilometragem atual do veículo", min_value=0.0, step=0.1, format="%.1f")
        preco = st.number_input("Preço do litro (R$)", min_value=0.0, step=0.001, format="%.3f")

    st.caption("Informe a quilometragem total que aparece no painel do veículo. Para calcular o consumo corretamente, procure registrar abastecimentos com tanque cheio.")
    submitted = st.form_submit_button("SALVAR ABASTECIMENTO", type="primary")

    if submitted:
        data_str = data_abast.strftime("%Y-%m-%d")
        registros = st.session_state.registros

        if km < 0 or valor <= 0 or preco <= 0:
            st.error("Confira os valores informados. Valor e preço devem ser maiores que zero.")
        elif any(r["data"] == data_str and r["km"] == km for r in registros):
            st.error("Este abastecimento já foi cadastrado.")
        elif registros and km <= max(r["km"] for r in registros):
            st.error("A quilometragem deve ser maior que a do último abastecimento.")
        else:
            registros.append({
                "id": int(datetime.now().timestamp() * 1000),
                "data": data_str,
                "km": float(km),
                "valor": float(valor),
                "preco": float(preco),
                "litros": float(valor / preco),
            })
            registros.sort(key=lambda item: item["km"])
            st.success("Abastecimento registrado com sucesso!")
            st.rerun()

st.divider()

# 3. Resumo do mês atual
st.subheader("📊 Resumo do mês atual")
m1, m2 = st.columns(2)
m1.metric("Gasto no mês", formatar_moeda(metricas["gasto_mes"]))
m2.metric("Abastecimentos", str(metricas["quantidade_mes"]))

st.divider()

# 4. Histórico de abastecimentos
st.subheader("📋 Histórico de abastecimentos")

if not st.session_state.registros:
    st.info("Nenhum abastecimento cadastrado.")
else:
    linhas_tabela = []
    for i, r in enumerate(st.session_state.registros):
        anterior = st.session_state.registros[i - 1] if i > 0 else None
        km_rodados = (r["km"] - anterior["km"]) if anterior else 0.0
        consumo = (km_rodados / r["litros"]) if (anterior and r["litros"] > 0) else 0.0

        data_br = datetime.strptime(r["data"], "%Y-%m-%d").strftime("%d/%m/%Y")
        linhas_tabela.append({
            "Data": data_br,
            "KM atual": formatar_numero(r["km"]),
            "KM rodados": f"{formatar_numero(km_rodados)} km" if anterior else "Referência",
            "Litros": f"{formatar_numero(r['litros'])} L",
            "Valor": formatar_moeda(r["valor"]),
            "Consumo": f"{formatar_numero(consumo)} km/L" if consumo else "--",
        })

    df_exibicao = pd.DataFrame(linhas_tabela)
    st.dataframe(df_exibicao, use_container_width=True, hide_index=True)
    st.caption("O primeiro abastecimento é usado como referência e não possui consumo calculado, pois ainda não há quilometragem anterior.")

    # Opção para excluir um lançamento específico
    with st.expander("Gerenciar / Excluir registros"):
        opcoes = {
            f"{datetime.strptime(r['data'], '%Y-%m-%d').strftime('%d/%m/%Y')} - {formatar_numero(r['km'])} km ({formatar_moeda(r['valor'])})": r["id"]
            for r in st.session_state.registros
        }
        escolha = st.selectbox("Selecione o abastecimento para remover:", list(opcoes.keys()))
        if st.button("Excluir registro selecionado"):
            id_remover = opcoes[escolha]
            st.session_state.registros = [r for r in st.session_state.registros if r["id"] != id_remover]
            st.rerun()

    # Botões de exportação (CSV e JSON)
    col_exp1, col_exp2, _ = st.columns([1, 1, 3])
    with col_exp1:
        df_csv = pd.DataFrame([
            {
                "Data": r["data"],
                "KM": r["km"],
                "Valor": r["valor"],
                "Preço litro": r["preco"],
                "Litros": round(r["litros"], 4),
            }
            for r in st.session_state.registros
        ])
        csv_bytes = df_csv.to_csv(sep=";", index=False).encode("utf-8-sig")
        st.download_button(
            label="EXPORTAR CSV",
            data=csv_bytes,
            file_name="abastecimentos.csv",
            mime="text/csv",
        )

    with col_exp2:
        json_str = json.dumps(st.session_state.registros, indent=2, ensure_ascii=False)
        st.download_button(
            label="FAZER BACKUP (JSON)",
            data=json_str.encode("utf-8"),
            file_name="backup-combustivel.json",
            mime="application/json",
        )