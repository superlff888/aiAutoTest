


"""
处理agent的结果
"""


def handle_agent_output(response):
    """处理agent的输出结果"""
    for chunk in response:
        if chunk['type'] == "messages":
            print(chunk['data'][0].content, end='')
        elif chunk['type'] == "updates":
            for step, data in chunk['data'].items():
                if step == "model":
                    print('🤖=================【调用大模型执行结果】========步骤完成=============')
                elif step == "tools":
                    print('🔧===================【调用工具返回结果】========步骤完成=============')
                for block in data['messages'][-1].content_blocks:
                    if block['type'] == "text":
                        print(block['text'])
                    elif block['type'] == "tool_call":
                        print(f"🔧工具:{block['name']},参数为：{block['args']}")
        elif chunk['type'] == 'custom':
            print("✅自定义输出：", chunk['data'])
