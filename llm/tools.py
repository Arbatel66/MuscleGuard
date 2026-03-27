#这里的description就相当于调用工具的system_prompt，只要create引用了tools就行
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_1rm",
            "description": "根据本组重量和次数，用 Epley 公式估算用户的理论最大力量(1RM)。用于评估本组训练强度是否合理，以及对比历史进步情况。",
            "parameters": {
                "type": "object",
                "properties": {
                    "weight": {
                        "type": "number",
                        "description": "本组使用的重量，单位 kg"
                    },
                    "reps": {
                        "type": "integer",
                        "description": "本组完成的次数"
                    }
                },
                "required": ["weight", "reps"]
            }
        }
    }
]