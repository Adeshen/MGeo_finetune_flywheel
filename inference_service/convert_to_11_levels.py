#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
from typing import Dict, List, Tuple, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def classify_elements_to_11_levels(entities: Dict[str, str], original_text: str) -> Dict[str, str]:
    """
    将实体数据转换为11级分类格式
    
    Args:
        entities: 实体字典，包含各种地址组件
        original_text: 原始地址文本
        
    Returns:
        包含11级分类的字典
    """
    try:
        addr = original_text
        indices = {}
        used_indices = set()  # 用于存储已经使用的索引范围

        def find_value(value: str, start: int = 0) -> Optional[Tuple[int, int]]:
            """在 addr 中从 start 位置开始查找 value"""
            pos = addr.find(value, start)
            if pos != -1:
                end = pos + len(value)
                # 检查该范围是否已经被使用
                if any(i in range(pos, end) for i in used_indices):
                    return find_value(value, end)  # 递归查找下一个匹配位置
                else:
                    used_indices.update(range(pos, end))
                    return (pos, end)
            return None

        # 构建索引映射
        for key, value in entities.items():
            if ',' in value:
                values = value.split(',')
                indices[key] = []
                for v in values:
                    v = v.strip()
                    index = find_value(v)
                    if index:
                        indices[key].append(index)
                    else:
                        logger.warning(f"Value '{v}' for key '{key}' not found in original address.")
            else:
                index = find_value(value)
                if index:
                    indices[key] = [index]
                else:
                    logger.warning(f"Value '{value}' for key '{key}' not found in original address.")

        # 检查POI相关标签
        poi_keys = ['poi', 'subpoi', 'community', 'devzone', 'village_group']
        poi_min_index = None
        for key in poi_keys:
            if key in indices and indices[key]:
                for start, end in indices[key]:
                    if poi_min_index is None or start < poi_min_index[0]:
                        poi_min_index = (start, end)
        
        # 检查行政区划相关标签
        admin_keys = ['prov', 'city', 'district', 'town']
        admin_max_index = None
        for key in admin_keys:
            if key in indices and indices[key]:
                for start, end in indices[key]:
                    if admin_max_index is None or start > admin_max_index[0]:
                        admin_max_index = (start, end)
        
        # 初始化11个级别
        level1 = entities.get('prov', '广东省')  # 默认广东省
        level2 = entities.get('city', '')
        level3 = entities.get('district', '')
        level4 = entities.get('town', '')
        level5 = ''
        level6 = ''
        level7 = ''
        level8 = ''
        level9 = ''
        level10 = ''
        level11 = ''
        
        # POI存在的情况
        if poi_min_index:
            level7 = addr[poi_min_index[0]:poi_min_index[1]].strip()
            
            # 前四级存在
            if admin_max_index:
                # 提取level5 (道路/方向)
                road_direction_keys = ['road', 'direction']
                min_road_direction_index = None
                max_road_direction_index = None
                for key in road_direction_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if (admin_max_index[1]-1 < start < poi_min_index[0]):
                                if min_road_direction_index is None or start < min_road_direction_index[0]:
                                    min_road_direction_index = (start, end)
                                if max_road_direction_index is None or start > max_road_direction_index[0]:
                                    max_road_direction_index = (start, end)

                if min_road_direction_index or max_road_direction_index:
                    level5 = addr[min_road_direction_index[0]:max_road_direction_index[1]].strip()
                
                # 提取level6 (路号)
                roadno_keys = ['roadno']
                min_roadno_index = None
                max_roadno_index = None
                for key in roadno_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if (max_road_direction_index and max_road_direction_index[1]-1 < start < poi_min_index[0]) or \
                            (not max_road_direction_index and admin_max_index[1]-1 < start < poi_min_index[0]):
                                if min_roadno_index is None or start < min_roadno_index[0]:
                                    min_roadno_index = (start, end)
                                if max_roadno_index is None or start > max_roadno_index[0]:
                                    max_roadno_index = (start, end)
                
                if min_roadno_index or max_roadno_index:
                    level6 = addr[min_roadno_index[0]:max_roadno_index[1]].strip()
            
            # 前四级不存在的情况
            else:
                # 提取level5 (道路/方向)
                road_direction_keys = ['road', 'direction']
                min_road_direction_index = None
                max_road_direction_index = None
                for key in road_direction_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if start < poi_min_index[0]:
                                if min_road_direction_index is None or start < min_road_direction_index[0]:
                                    min_road_direction_index = (start, end)
                                if max_road_direction_index is None or start > max_road_direction_index[0]:
                                    max_road_direction_index = (start, end)
                
                if min_road_direction_index or max_road_direction_index:
                    level5 = addr[min_road_direction_index[0]:max_road_direction_index[1]].strip()
                
                # 提取level6 (路号)
                roadno_keys = ['roadno']
                min_roadno_index = None
                max_roadno_index = None
                for key in roadno_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if (max_road_direction_index and max_road_direction_index[1]-1 < start < poi_min_index[0]) or \
                            (not max_road_direction_index and start < poi_min_index[0]):
                                if min_roadno_index is None or start < min_roadno_index[0]:
                                    min_roadno_index = (start, end)
                                if max_roadno_index is None or start > max_roadno_index[0]:
                                    max_roadno_index = (start, end)
                
                if min_roadno_index or max_roadno_index:
                    level6 = addr[min_roadno_index[0]:max_roadno_index[1]].strip()
            
            # 提取level8 (POI后的附加信息)
            additional_poi_keys = ['poi', 'subpoi', 'road', 'roadno', 'direction', 'community', 'devzone', 'village_group', 'houseno']
            min_additional_poi_index = None
            max_additional_poi_index = None
            for key in additional_poi_keys:
                if key in indices and indices[key]:
                    for start, end in indices[key]:
                        if poi_min_index[1]-1 < start:
                            if min_additional_poi_index is None or start < min_additional_poi_index[0]:
                                min_additional_poi_index = (start, end)
                            if max_additional_poi_index is None or start > max_additional_poi_index[0]:
                                max_additional_poi_index = (start, end)
            
            if min_additional_poi_index or max_additional_poi_index:
                level8 = addr[min_additional_poi_index[0]:max_additional_poi_index[1]].strip()
            
            # 提取level9 (小区号)
            cellno_keys = ['cellno']
            min_cellno_index = None
            max_cellno_index = None
            for key in cellno_keys:
                if key in indices and indices[key]:
                    for start, end in indices[key]:
                        if (max_additional_poi_index and start > max_additional_poi_index[1]-1) or \
                           (not max_additional_poi_index and start > poi_min_index[1]-1):
                            if min_cellno_index is None or start < min_cellno_index[0]:
                                min_cellno_index = (start, end)
                            if max_cellno_index is None or start > max_cellno_index[0]:
                                max_cellno_index = (start, end)
            
            if min_cellno_index or max_cellno_index:
                level9 = addr[min_cellno_index[0]:max_cellno_index[1]].strip()
            
            # 提取level10 (楼层号)
            latest_keys = [admin_max_index, max_road_direction_index, max_roadno_index, poi_min_index, max_additional_poi_index, max_cellno_index]
            valid_latest_keys = [x for x in latest_keys if x]
            latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
            
            if latest_max_index:
                floorno_keys = ['floorno']
                min_floorno_index = None
                max_floorno_index = None
                for key in floorno_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if start > latest_max_index[1]-1:
                                if min_floorno_index is None or start < min_floorno_index[0]:
                                    min_floorno_index = (start, end)
                                if max_floorno_index is None or start > max_floorno_index[0]:
                                    max_floorno_index = (start, end)
                
                if min_floorno_index or max_floorno_index:
                    level10 = addr[min_floorno_index[0]:max_floorno_index[1]].strip()
                
                # 提取level11 (房间号)
                latest_keys.append(max_floorno_index)
                valid_latest_keys = [x for x in latest_keys if x]
                latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
                
                if latest_max_index:
                    roomno_keys = ['roomno']
                    min_roomno_index = None
                    max_roomno_index = None
                    for key in roomno_keys:
                        if key in indices and indices[key]:
                            for start, end in indices[key]:
                                if start > latest_max_index[1]-1:
                                    if min_roomno_index is None or start < min_roomno_index[0]:
                                        min_roomno_index = (start, end)
                                    if max_roomno_index is None or start > max_roomno_index[0]:
                                        max_roomno_index = (start, end)
                    
                    if min_roomno_index or max_roomno_index:
                        level11 = addr[min_roomno_index[0]:max_roomno_index[1]].strip()
        
        # POI不存在的情况
        else:
            level7 = ''
            level8 = ''
            level9 = ''
            level10 = ''
            level11 = ''
            
            # 前四级存在
            if admin_max_index:
                # 提取level5 (道路/方向)
                road_direction_keys = ['road', 'direction']
                min_road_direction_index = None
                max_road_direction_index = None
                for key in road_direction_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if admin_max_index[1]-1 < start:
                                if min_road_direction_index is None or start < min_road_direction_index[0]:
                                    min_road_direction_index = (start, end)
                                if max_road_direction_index is None or start > max_road_direction_index[0]:
                                    max_road_direction_index = (start, end)

                if min_road_direction_index or max_road_direction_index:
                    level5 = addr[min_road_direction_index[0]:max_road_direction_index[1]].strip()
                
                # 提取level6 (路号)
                roadno_keys = ['roadno']
                min_roadno_index = None
                max_roadno_index = None
                for key in roadno_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if (max_road_direction_index and max_road_direction_index[1]-1 < start) or \
                            (not max_road_direction_index and admin_max_index[1]-1 < start):
                                if min_roadno_index is None or start < min_roadno_index[0]:
                                    min_roadno_index = (start, end)
                                if max_roadno_index is None or start > max_roadno_index[0]:
                                    max_roadno_index = (start, end)
                
                if min_roadno_index or max_roadno_index:
                    level6 = addr[min_roadno_index[0]:max_roadno_index[1]].strip()
                
                # 提取level8-11
                latest_keys = [admin_max_index, max_road_direction_index, max_roadno_index]
                valid_latest_keys = [x for x in latest_keys if x]
                latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
                
                if latest_max_index:
                    # level8 (房屋号)
                    additional_poi_keys = ['houseno']
                    min_additional_poi_index = None
                    max_additional_poi_index = None
                    for key in additional_poi_keys:
                        if key in indices and indices[key]:
                            for start, end in indices[key]:
                                if start > latest_max_index[1]-1:
                                    if min_additional_poi_index is None or start < min_additional_poi_index[0]:
                                        min_additional_poi_index = (start, end)
                                    if max_additional_poi_index is None or start > max_additional_poi_index[0]:
                                        max_additional_poi_index = (start, end)
                    
                    if min_additional_poi_index or max_additional_poi_index:
                        level8 = addr[min_additional_poi_index[0]:max_additional_poi_index[1]].strip()
                    
                    # 更新latest_keys
                    latest_keys.append(max_additional_poi_index)
                    valid_latest_keys = [x for x in latest_keys if x]
                    latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
                    
                    if latest_max_index:
                        # level9 (单元号)
                        cellno_keys = ['cellno']
                        min_cellno_index = None
                        max_cellno_index = None
                        for key in cellno_keys:
                            if key in indices and indices[key]:
                                for start, end in indices[key]:
                                    if start > latest_max_index[1]-1:
                                        if min_cellno_index is None or start < min_cellno_index[0]:
                                            min_cellno_index = (start, end)
                                        if max_cellno_index is None or start > max_cellno_index[0]:
                                            max_cellno_index = (start, end)
                        
                        if min_cellno_index or max_cellno_index:
                            level9 = addr[min_cellno_index[0]:max_cellno_index[1]].strip()
                        
                        # 更新latest_keys
                        latest_keys.append(max_cellno_index)
                        valid_latest_keys = [x for x in latest_keys if x]
                        latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
                        
                        if latest_max_index:
                            # level10 (楼层号)
                            floorno_keys = ['floorno']
                            min_floorno_index = None
                            max_floorno_index = None
                            for key in floorno_keys:
                                if key in indices and indices[key]:
                                    for start, end in indices[key]:
                                        if start > latest_max_index[1]-1:
                                            if min_floorno_index is None or start < min_floorno_index[0]:
                                                min_floorno_index = (start, end)
                                            if max_floorno_index is None or start > max_floorno_index[0]:
                                                max_floorno_index = (start, end)
                            
                            if min_floorno_index or max_floorno_index:
                                level10 = addr[min_floorno_index[0]:max_floorno_index[1]].strip()
                            
                            # 更新latest_keys
                            latest_keys.append(max_floorno_index)
                            valid_latest_keys = [x for x in latest_keys if x]
                            latest_max_index = max(valid_latest_keys, key=lambda x: x[1]) if valid_latest_keys else None
                            
                            if latest_max_index:
                                # level11 (房间号)
                                roomno_keys = ['roomno']
                                min_roomno_index = None
                                max_roomno_index = None
                                for key in roomno_keys:
                                    if key in indices and indices[key]:
                                        for start, end in indices[key]:
                                            if start > latest_max_index[1]-1:
                                                if min_roomno_index is None or start < min_roomno_index[0]:
                                                    min_roomno_index = (start, end)
                                                if max_roomno_index is None or start > max_roomno_index[0]:
                                                    max_roomno_index = (start, end)
                                
                                if min_roomno_index or max_roomno_index:
                                    level11 = addr[min_roomno_index[0]:max_roomno_index[1]].strip()
            
            # 前四级不存在的情况
            else:
                # 提取道路信息到level5
                road_direction_keys = ['road', 'direction']
                min_road_direction_index = None
                max_road_direction_index = None
                for key in road_direction_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if min_road_direction_index is None or start < min_road_direction_index[0]:
                                min_road_direction_index = (start, end)
                            if max_road_direction_index is None or start > max_road_direction_index[0]:
                                max_road_direction_index = (start, end)
                
                if min_road_direction_index or max_road_direction_index:
                    level5 = addr[min_road_direction_index[0]:max_road_direction_index[1]].strip()
                
                # 提取路号到level6
                roadno_keys = ['roadno']
                min_roadno_index = None
                max_roadno_index = None
                for key in roadno_keys:
                    if key in indices and indices[key]:
                        for start, end in indices[key]:
                            if (max_road_direction_index and start > max_road_direction_index[1]-1) or \
                            (not max_road_direction_index):
                                if min_roadno_index is None or start < min_roadno_index[0]:
                                    min_roadno_index = (start, end)
                                if max_roadno_index is None or start > max_roadno_index[0]:
                                    max_roadno_index = (start, end)
                
                if min_roadno_index or max_roadno_index:
                    level6 = addr[min_roadno_index[0]:max_roadno_index[1]].strip()
        
        # 构建结果字典
        levels = {
            'level1': level1,
            'level2': level2,
            'level3': level3,
            'level4': level4,
            'level5': level5,
            'level6': level6,
            'level7': level7,
            'level8': level8,
            'level9': level9,
            'level10': level10,
            'level11': level11
        }
        
        # 计算剩余部分作为备注
        used_indices_final = set()
        for key, value in indices.items():
            for start, end in value:
                used_indices_final.update(range(start, end))
        
        remaining_parts = [addr[i] for i in range(len(addr)) if i not in used_indices_final]
        remark = ''.join(remaining_parts).strip()
        
        levels['remark'] = remark
        levels['original_text'] = original_text
        
        return levels
        
    except Exception as e:
        logger.error(f"classify_elements error: {e}")
        return {
            'level1': '',
            'level2': '',
            'level3': '',
            'level4': '',
            'level5': '',
            'level6': '',
            'level7': '',
            'level8': '',
            'level9': '',
            'level10': '',
            'level11': '',
            'remark': '',
            'original_text': original_text,
            'error': str(e)
        }


def convert_formatted_to_11_levels(input_file: str, output_file: str):
    """
    将formatted_detailed.json转换为11级分类格式
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
    """
    try:
        results = []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                    original_text = data.get('original_text', '')
                    entities = data.get('entities', {})
                    
                    # 转换为11级分类
                    levels_result = classify_elements_to_11_levels(entities, original_text)
                    results.append(levels_result)
                    
                    logger.info(f"Processed line {line_num}: {original_text}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error at line {line_num}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # 保存结果
        with open(output_file, 'w', encoding='utf-8') as f:
            for result in results:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        logger.info(f"Successfully converted {len(results)} records to {output_file}")
        
        # 打印统计信息
        print(f"\n转换完成！")
        print(f"输入文件: {input_file}")
        print(f"输出文件: {output_file}")
        print(f"处理记录数: {len(results)}")
        
        # 显示前几个示例
        print(f"\n前3个转换示例:")
        for i, result in enumerate(results[:3]):
            print(f"\n示例 {i+1}:")
            print(f"原始文本: {result['original_text']}")
            for j in range(1, 12):
                level_value = result.get(f'level{j}', '')
                if level_value:
                    print(f"  level{j}: {level_value}")
            if result.get('remark'):
                print(f"  备注: {result['remark']}")
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        raise


if __name__ == "__main__":
    input_file = "/root/yuedongzhong/mgeo_finetune/result/formatted_detailed.json"
    output_file = "/root/yuedongzhong/mgeo_finetune/result/11_levels_result.json"
    
    convert_formatted_to_11_levels(input_file, output_file)