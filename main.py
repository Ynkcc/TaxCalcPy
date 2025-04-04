# main.py
import yaml
from datetime import datetime

# 个税税率表（累计预扣预缴）
TAX_RATES = [
    (36000, 0.03, 0),
    (144000, 0.10, 2520),
    (300000, 0.20, 16920),
    (420000, 0.25, 31920),
    (660000, 0.30, 52920),
    (960000, 0.35, 85920),
    (float('inf'), 0.45, 181920)
]

def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def generate_months(start_date, end_date):
    months = []
    current = datetime.strptime(start_date, "%Y-%m")
    end = datetime.strptime(end_date, "%Y-%m")
    while current <= end:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months

def get_salary_adjustments(adjustments):
    return sorted([
        (datetime.strptime(adj['date'], "%Y-%m"), adj['new_salary'])
        for adj in adjustments
    ], key=lambda x: x[0])

def calculate_tax(taxable_income):
    for max_income, rate, deduction in TAX_RATES:
        if taxable_income <= max_income:
            return max(taxable_income * rate - deduction, 0.0)
    return 0.0

def main():
    config = load_config("config.yaml")
    months = generate_months(config['start_date'], config['end_date'])
    adjustments = get_salary_adjustments(config.get('salary_adjustments', []))
    leave_days = config.get('leave_days', {}) or {}
    
    current_salary = config['monthly_salary']
    adj_idx = 0
    start_year = datetime.strptime(config['start_date'], "%Y-%m").year
    cumulative = {}

    results = []
    
    for month_str in months:
        current_month = datetime.strptime(month_str, "%Y-%m")
        year = current_month.year
        month_num = current_month.month

        # 初始化年度累积数据
        if year not in cumulative:
            if year == start_year:
                cumulative[year] = {
                    'income': config['initial_accumulated']['income'],
                    'social_insurance': 0.0,
                    'special_deduction': config['initial_accumulated']['special_deduction'],
                    'tax_paid': config['initial_accumulated']['tax_paid']
                }
            else:
                cumulative[year] = {
                    'income': 0.0,
                    'social_insurance': 0.0,
                    'special_deduction': 0.0,
                    'tax_paid': 0.0
                }
        current_cumulative = cumulative[year]

        # 处理调薪
        while adj_idx < len(adjustments) and adjustments[adj_idx][0] <= current_month:
            current_salary = adjustments[adj_idx][1]
            adj_idx += 1

        # 计算实际工资
        work_days = leave_days.get(month_str, 21.75)
        actual_salary = current_salary * work_days / 21.75

        # 计算五险一金（按原月薪计算）
        insurance = current_salary * (
            config['insurance_rates']['pension'] +
            config['insurance_rates']['unemployment'] +
            config['insurance_rates']['medical']
        )
        housing_fund = current_salary * config['housing_fund_rate']
        monthly_social_insurance = insurance + housing_fund

        # 更新累积值
        current_cumulative['income'] += actual_salary
        current_cumulative['social_insurance'] += monthly_social_insurance

        # 计算应纳税所得额
        basic_deduction = 5000 * month_num
        taxable_income = (current_cumulative['income'] 
                          - basic_deduction 
                          - current_cumulative['social_insurance'] 
                          - current_cumulative['special_deduction'])

        # 计算税款
        total_tax = calculate_tax(taxable_income)
        current_month_tax = max(total_tax - current_cumulative['tax_paid'], 0.0)
        current_cumulative['tax_paid'] += current_month_tax

        results.append({
            "month": month_str,
            "salary": round(actual_salary, 2),
            "monthly_deduction": round(monthly_social_insurance, 2),
            "cumulative_income": round(current_cumulative['income'], 2),
            "taxable_income": round(taxable_income, 2),
            "tax": round(current_month_tax, 2),
            "cumulative_tax": round(current_cumulative['tax_paid'], 2)
        })

    # 打印结果
    print(f"{'Month':>8}{'Salary':>12}{'三险一金扣除':>8}{'本年度收入':>10}{'本年度计税收入':>12}{'当月税款':>8}{'年度累积税额':>8}")
    for r in results:
        print(f"{r['month']:>8}"
              f"{r['salary']:>12.2f}"
              f"{r['monthly_deduction']:>12.2f}"
              f"{r['cumulative_income']:>16.2f}"
              f"{r['taxable_income']:>16.2f}"
              f"{r['tax']:>12.2f}"
              f"{r['cumulative_tax']:>16.2f}")

    import pandas as pd

    # 转换结果为DataFrame并重命名列
    df = pd.DataFrame(results)
    df = df.rename(columns={
        'month': 'Month',
        'salary': 'Salary',
        'monthly_deduction': '三险一金扣除',
        'cumulative_income': '本年度收入',
        'taxable_income': '本年度计税收入',
        'tax': '当月税款',
        'cumulative_tax': "本年度累积申报税额",
    })

    # 调整列顺序（如果需要）
    df = df[['Month', 'Salary', '三险一金扣除', '本年度收入', '本年度计税收入', '当月税款', "本年度累积申报税额",]]

    # 保存到Excel
    df.to_excel("个税计算结果.xlsx", 
            index=False,
            float_format="%.2f")  # 保持两位小数

if __name__ == "__main__":
    main()
