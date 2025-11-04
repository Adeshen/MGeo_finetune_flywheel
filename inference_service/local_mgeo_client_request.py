#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
from typing import Dict, Any, Optional

def post_standardaddr(data: Dict[str, Any], 
                     url: str = "http://127.0.0.1:7869/standardaddr",
                     timeout: int = 30) -> Optional[Dict[str, Any]]:
    """
    向标准地址接口发送POST请求
    
    Args:
        data: 要发送的数据字典
        url: 服务URL
        timeout: 请求超时时间（秒）
        
    Returns:
        响应数据字典，如果请求失败返回None
    """
    try:
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        response = requests.post(
            url=url,
            json=data,
            headers=headers,
            timeout=timeout
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
        return None

def main():
    print("MGeo地址标准化客户端测试")
    
    # 示例用法 - 与原web_test.py保持一致的接口
    sample_data = {
        "address": "凤馨苑十一街3座9楼、3楼、6楼、12楼、16楼",
        # "address": "广东东莞市东莞市南城区石竹新花园石竹苑12栋12座1002",
        "address": "五楼501",
        "address": "花都区新华镇106国道旁荣翠轩小区A4-8层",
        "address": "番禺区沙湾镇市良路荷景一区三街2座全覆盖",
        "address": "白云区太和镇大源村田新路40号105房",
        "city": "广州",
        "user_id": "zhongyd7"
    }
    
    print(f"请求数据: {json.dumps(sample_data, ensure_ascii=False, indent=2)}")
    
    result = post_standardaddr(sample_data,
    url="http://127.0.0.1:7869/standardaddr",
    )
    
    if result:
        print("请求成功!")
        print(f"响应数据: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 如果成功，显示11级分类结果
        # if result.get('success') and 'levels_result' in result:
        #     print("\n=== 11级分类结果 ===")
        #     levels = result['levels_result']
        #     for level, value in levels.items():
        #         if value and value.strip():
        #             print(f"{level}: {value}")
    else:
        print("请求失败!")

if __name__ == "__main__":
    main()