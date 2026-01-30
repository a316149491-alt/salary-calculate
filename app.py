import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- 页面配置 ---
st.set_page_config(
    page_title="上海市税后工资计算器",
    page_icon="💰",
    layout="wide"
)

# --- 样式美化 ---
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    .stMetric {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 常量配置 (2025.7 - 2026.6 上海标准) ---
SS_UPPER = 37302
SS_LOWER = 7460
TAX_BRACKETS = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float('inf'), 0.45, 181920)
]

# --- 侧边栏：输入参数 ---
with st.sidebar:
    st.header("⚙️ 输入参数")
    gross_salary = st.number_input("月税前工资 (元)", value=65000, step=1000)
    pf_rate = st.select_slider("住房公积金比例 (%)", options=[5, 6, 7], value=7)
    special_deduction = st.number_input("每月专项附加扣除 (元)", value=0, help="如子女教育、房贷利息、租房、赡养老人等")
    
    st.divider()
    st.info(f"**当前政策依据**\n\n上海社保上限: {SS_UPPER}元\n上海社保下限: {SS_LOWER}元")

# --- 计算核心逻辑 ---
def calculate_salary(gross, pf_pct, deduction):
    # 1. 确定基数
    ss_base = min(max(gross, SS_LOWER), SS_UPPER)
    
    # 2. 计算固定扣除 (个人部分)
    pension = ss_base * 0.08
    medical = ss_base * 0.02
    unemployment = ss_base * 0.005
    social_security = pension + medical + unemployment
    provident_fund = ss_base * (pf_pct / 100)
    total_fixed_deduction = social_security + provident_fund
    
    # 3. 逐月累计计算个税
    cumulative_taxable_income = 0
    cumulative_tax_paid = 0
    monthly_details = []
    
    for month in range(1, 13):
        # 累计应纳税所得额 = 累计税前 - 累计起征点 - 累计社保公积金 - 累计专项扣除
        current_month_taxable = gross - 5000 - total_fixed_deduction - deduction
        cumulative_taxable_income += current_month_taxable
        
        # 匹配税率档位
        tax_to_pay_total = 0
        for limit, rate, quick_sub in TAX_BRACKETS:
            if cumulative_taxable_income <= limit:
                tax_to_pay_total = cumulative_taxable_income * rate - quick_sub
                break
        
        # 当月个税 = 累计应纳税额 - 已缴税额
        monthly_tax = max(0, tax_to_pay_total - cumulative_tax_paid)
        cumulative_tax_paid += monthly_tax
        take_home = gross - total_fixed_deduction - monthly_tax
        
        monthly_details.append({
            "月份": f"{month}月",
            "税前": gross,
            "五险一金": round(total_fixed_deduction, 2),
            "个税": round(monthly_tax, 2),
            "到手现金": round(take_home, 2)
        })
        
    return ss_base, monthly_details, cumulative_tax_paid, total_fixed_deduction * 12

ss_base, monthly_list, total_tax, total_ss_pf = calculate_salary(gross_salary, pf_rate, special_deduction)
df = pd.DataFrame(monthly_list)
annual_take_home = df["到手现金"].sum()

# --- 主界面展示 ---
st.title("💰 上海市税后工资计算器 (2025-2026)")

# 第一行：数据卡片
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("全年总到手 (现金)", f"¥ {annual_take_home:,.2f}")
with col2:
    st.metric("全年总个税", f"¥ {total_tax:,.2f}", delta_color="inverse")
with col3:
    st.metric("实际社保缴纳基数", f"¥ {ss_base:,.0f}")

# 第二行：图表与详细说明
st.divider()
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("月度到手现金趋势")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["月份"], y=df["到手现金"], name="到手金额", line=dict(color='#2563eb', width=4)))
    fig.add_trace(go.Bar(x=df["月份"], y=df["个税"], name="个人所得税", marker_color='#ef4444', opacity=0.6))
    fig.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=20, b=0), height=400)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("支出构成")
    pie_data = {
        "项目": ["到手现金", "个税", "五险一金"],
        "金额": [annual_take_home, total_tax, total_ss_pf]
    }
    fig_pie = go.Figure(data=[go.Pie(labels=pie_data["项目"], values=pie_data["金额"], hole=.4)])
    fig_pie.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=350, showlegend=True)
    st.plotly_chart(fig_pie, use_container_width=True)

# 第三行：详细数据表格
st.subheader("📋 1-12月明细清单")
st.dataframe(df, use_container_width=True, hide_index=True)

st.markdown("""
> **计算逻辑说明：**
> 1. **累计预扣法**：根据中国税法，高薪人群由于累计收入增加，税率档位会逐步提升（3% -> 10% -> 20%...），因此年底的到手金额通常低于年初。
> 2. **封顶基数**：计算器已自动根据上海最新平均工资水平调整，月薪超过 37,302 元的部分不计入社保公积金基数。
""")