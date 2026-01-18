from django.template import Template, Context

# 测试sum过滤器
print("Testing sum filter...")

try:
    # 测试1：基本使用
    template = Template('{{ values|sum }}')
    context = Context({'values': [1, 2, 3, 4, 5]})
    result = template.render(context)
    print(f"Test 1 (basic sum): PASS - Result: {result}")
except Exception as e:
    print(f"Test 1 (basic sum): FAIL - Error: {e}")

try:
    # 测试2：带字段名的sum过滤器
    template = Template('{{ objects|sum:"field" }}')
    context = Context({
        'objects': [
            {'field': 10}, 
            {'field': 20}, 
            {'field': 30}
        ]
    })
    result = template.render(context)
    print(f"Test 2 (sum with field): PASS - Result: {result}")
except Exception as e:
    print(f"Test 2 (sum with field): FAIL - Error: {e}")

try:
    # 测试3：模拟我们的报表数据结构
    template = Template('{{ report_data.business_type_data.values|sum:"foot_traffic" }}')
    context = Context({
        'report_data': {
            'business_type_data': {
                '零售': {'foot_traffic': 100},
                '餐饮': {'foot_traffic': 200}
            }
        }
    })
    result = template.render(context)
    print(f"Test 3 (report data structure): PASS - Result: {result}")
except Exception as e:
    print(f"Test 3 (report data structure): FAIL - Error: {e}")
