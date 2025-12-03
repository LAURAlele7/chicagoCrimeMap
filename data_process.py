import pandas as pd
import json
from datetime import datetime
import numpy as np

# 1. 加载和预处理数据
def load_and_preprocess_data(file_path):
    """加载犯罪数据并进行初步清理"""
    df = pd.read_csv(file_path)
    
    print(f"原始数据行数: {len(df)}")
    
    # 日期标准化
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    # # 过滤2024年数据
    # df = df[df['Date'].dt.year == 2024]
    # print(f"2024年数据行数: {len(df)}")
    df = df[(df['Date'].dt.year >= 2014) & (df['Date'].dt.year <= 2024)]
    print(f"10年数据行数: {len(df)}")
    # 移除无效坐标
    df = df[(df['Latitude'] != 0) & (df['Longitude'] != 0)]
    df = df.dropna(subset=['Latitude', 'Longitude'])
    print(f"有效坐标数据行数: {len(df)}")
    
    # 添加月份列
    df['Month'] = df['Date'].dt.month
    df['Month_Year'] = df['Date'].dt.strftime('%Y-%m')
    
    # 标准化犯罪类型名称
    crime_type_mapping = {
        'WEAPONS VIOLATION': 'Weapons Violation',
        'NARCOTICS': 'Narcotics', 
        'CRIMINAL SEXUAL ASSAULT': 'Criminal Sexual Assault'
    }
    
    df['Primary Type'] = df['Primary Type'].str.upper()
    df['Primary Type'] = df['Primary Type'].replace(crime_type_mapping)
    
    # 确保District列是数值型
    df['District'] = pd.to_numeric(df['District'], errors='coerce')
    df = df.dropna(subset=['District'])
    df['District'] = df['District'].astype(int)
    print(f"有效District数据行数: {len(df)}")
    
    # 转换布尔列
    df['Domestic'] = df['Domestic'].astype(bool)
    df['Arrest'] = df['Arrest'].astype(bool)
    
    return df

def convert_to_serializable(obj):
    """将对象转换为JSON可序列化的格式"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif pd.isna(obj):
        return None
    else:
        return obj

# 2. 为趋势图准备数据
def prepare_trend_data(df):
    """准备趋势图数据 - 月度聚合"""
    print("准备趋势图数据...")
    
    # 按月份和犯罪类型聚合
    monthly_totals = df.groupby('Month_Year').size().reset_index(name='total_crimes')
    monthly_totals = monthly_totals.sort_values('Month_Year')
    
    crime_types = ['Weapons Violation', 'Narcotics', 'Criminal Sexual Assault']
    crime_type_data = []
    
    for crime_type in crime_types:
        crime_counts = df[df['Primary Type'] == crime_type].groupby('Month_Year').size().reset_index(name='count')
        crime_counts['crime_type'] = crime_type
        crime_type_data.append(crime_counts)
    
    crime_type_df = pd.concat(crime_type_data, ignore_index=True)
    
    # 合并数据
    trend_data = {
        'monthly_totals': convert_to_serializable(monthly_totals.to_dict('records')),
        'crime_type_trends': convert_to_serializable(crime_type_df.to_dict('records'))
    }
    
    print(f"趋势数据: {len(trend_data['monthly_totals'])} 个月份")
    return trend_data

# 3. 为地图和饼图准备数据
def prepare_map_and_pie_data(df):
    """准备地图和饼图数据"""
    print("准备地图和饼图数据...")
    
    # 按区域和月份聚合
    district_monthly = df.groupby(['District', 'Month_Year']).agg({
        'ID': 'count',  # 总案件数
        'Domestic': 'sum',  # 家庭暴力案件数
        'Arrest': 'sum',   # 逮捕案件数
    }).reset_index()
    
    district_monthly.rename(columns={'ID': 'total_crimes'}, inplace=True)
    
    print(f"处理的区域数量: {district_monthly['District'].nunique()}")
    print(f"处理的月份数量: {district_monthly['Month_Year'].nunique()}")
    
    # 计算百分比
    district_monthly['domestic_percentage'] = (district_monthly['Domestic'] / district_monthly['total_crimes'] * 100).round(2)
    district_monthly['arrest_percentage'] = (district_monthly['Arrest'] / district_monthly['total_crimes'] * 100).round(2)
    
    # 为特定犯罪类型添加计数
    crime_types = ['Weapons Violation', 'Narcotics', 'Criminal Sexual Assault']
    
    for crime_type in crime_types:
        crime_counts = df[df['Primary Type'] == crime_type].groupby(['District', 'Month_Year']).size().reset_index(name=f'{crime_type.lower().replace(" ", "_")}_count')
        district_monthly = district_monthly.merge(crime_counts, on=['District', 'Month_Year'], how='left')
        district_monthly[f'{crime_type.lower().replace(" ", "_")}_count'] = district_monthly[f'{crime_type.lower().replace(" ", "_")}_count'].fillna(0).astype(int)
    
    # 计算犯罪类型构成百分比
    for crime_type in crime_types:
        col_name = crime_type.lower().replace(" ", "_")
        district_monthly[f'{col_name}_percentage'] = (district_monthly[f'{col_name}_count'] / district_monthly['total_crimes'] * 100).round(2)
        # 处理除零情况
        district_monthly[f'{col_name}_percentage'] = district_monthly[f'{col_name}_percentage'].fillna(0)
    
    # 准备城市级别的饼图数据（按月）
    city_level_data = prepare_city_level_pie_data(df)
    
    # 准备区域级别的详细数据
    district_data = {}
    for district in district_monthly['District'].unique():
        district_df = district_monthly[district_monthly['District'] == district]
        district_data[str(district)] = convert_to_serializable(district_df.to_dict('records'))
    
    # 准备按月聚合的数据
    monthly_data = {}
    for month in district_monthly['Month_Year'].unique():
        month_df = district_monthly[district_monthly['Month_Year'] == month]
        monthly_data[month] = convert_to_serializable(month_df.to_dict('records'))
    
    map_pie_data = {
        'district_monthly': convert_to_serializable(district_monthly.to_dict('records')),
        'district_data': district_data,
        'monthly_data': monthly_data,
        'city_level': city_level_data,
        'available_months': convert_to_serializable(sorted(df['Month_Year'].unique())),
        'available_districts': convert_to_serializable(sorted(df['District'].unique()))
    }
    
    return map_pie_data

def prepare_city_level_pie_data(df):
    """准备城市级别的饼图数据（按月）"""
    print("准备城市级别饼图数据...")
    
    city_data = {}
    
    # 为每个月准备数据
    months = sorted(df['Month_Year'].unique())
    
    for month in months:
        month_df = df[df['Month_Year'] == month]
        total_crimes = len(month_df)
        
        if total_crimes == 0:
            continue
            
        # 家庭暴力比例
        domestic_percentage = round(month_df['Domestic'].sum() / total_crimes * 100, 2)
        
        # 逮捕比例
        arrest_percentage = round(month_df['Arrest'].sum() / total_crimes * 100, 2)
        
        # 特定犯罪类型比例
        crime_types = ['Weapons Violation', 'Narcotics', 'Criminal Sexual Assault']
        crime_type_percentages = {}
        
        for crime_type in crime_types:
            count = len(month_df[month_df['Primary Type'] == crime_type])
            percentage = round(count / total_crimes * 100, 2)
            crime_type_percentages[crime_type.lower().replace(" ", "_")] = percentage
        
        # 其他犯罪类型比例
        other_crimes = total_crimes - sum([len(month_df[month_df['Primary Type'] == crime_type]) for crime_type in crime_types])
        other_percentage = round(other_crimes / total_crimes * 100, 2)
        crime_type_percentages['other'] = other_percentage
        
        city_data[month] = {
            'total_crimes': int(total_crimes),
            'domestic_percentage': float(domestic_percentage),
            'arrest_percentage': float(arrest_percentage),
            'crime_type_percentages': {k: float(v) for k, v in crime_type_percentages.items()}
        }
    
    return city_data

# 4. 主处理函数
def main():
    """主处理函数"""
    try:
        # 加载数据
        # df = load_and_preprocess_data('chicago_crime_2024.csv')
        df = load_and_preprocess_data('crime_2014_2024.csv')
        # 准备趋势数据
        trend_data = prepare_trend_data(df)
        
        # 准备地图和饼图数据
        map_pie_data = prepare_map_and_pie_data(df)
        
        # 保存数据为JSON文件
        with open('trend_data_monthly.json', 'w') as f:
            json.dump(trend_data, f, indent=2)
        
        with open('map_pie_data_monthly.json', 'w') as f:
            json.dump(map_pie_data, f, indent=2)
        
        print("数据预处理完成！")
        print(f"生成的JSON文件:")
        print(f"- trend_data_monthly.json: 月度趋势图数据")
        print(f"- map_pie_data_monthly.json: 月度地图和饼图数据")
        
        # 打印一些统计信息
        print(f"\n数据统计:")
        print(f"总案件数: {len(df)}")
        print(f"涉及区域数: {df['District'].nunique()}")
        print(f"月份范围: {df['Month_Year'].min()} - {df['Month_Year'].max()}")
        print(f"犯罪类型分布:")
        for crime_type in ['Weapons Violation', 'Narcotics', 'Criminal Sexual Assault']:
            count = len(df[df['Primary Type'] == crime_type])
            print(f"  {crime_type}: {count} ({count/len(df)*100:.2f}%)")
        
        # 打印月度信息
        months = sorted(df['Month_Year'].unique())
        print(f"\n包含的月份: {', '.join(months)}")
        
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()