import json
import os
from typing import Dict, List, Any

class AddressFormatter:
    def __init__(self):
        """初始化地址格式化器"""
        # 定义实体类型的中文映射
        self.entity_mapping = {
            'prov': '省份',
            'city': '城市', 
            'district': '区县',
            'town': '街道/镇',
            'community': '社区/村',
            'road': '道路',
            'roadno': '门牌号',
            'poi': '兴趣点',
            'subpoi': '子兴趣点',
            'houseno': '楼栋号',
            'cellno': '单元号',
            'floorno': '楼层',
            'roomno': '房间号',
            'devzone': '开发区',
            'intersection': '路口',
            'assist': '辅助信息',
            'distance': '距离',
            'village_group': '村组'
        }
    
    def extract_entities_from_tokens(self, tokens: List[str], ner_tags: List[str]) -> Dict[str, List[str]]:
        """
        从tokens和NER标签中提取实体
        
        Args:
            tokens: 字符列表
            ner_tags: NER标签列表
            
        Returns:
            按实体类型分组的实体字典
        """
        entities = {}
        current_entity = None
        current_tokens = []
        
        for token, tag in zip(tokens, ner_tags):
            if tag.startswith('B-') or tag.startswith('S-'):
                # 保存之前的实体
                if current_entity and current_tokens:
                    entity_type = current_entity.split('-', 1)[1] if '-' in current_entity else current_entity
                    entity_text = ''.join(current_tokens)
                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].append(entity_text)
                
                # 开始新实体
                current_entity = tag
                current_tokens = [token]
                
                # 如果是S-标签，直接结束
                if tag.startswith('S-'):
                    entity_type = tag.split('-', 1)[1]
                    entity_text = ''.join(current_tokens)
                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].append(entity_text)
                    current_entity = None
                    current_tokens = []
                    
            elif tag.startswith('I-') and current_entity:
                # 继续当前实体
                current_tokens.append(token)
            elif tag.startswith('E-') and current_entity:
                # 结束当前实体
                current_tokens.append(token)
                entity_type = current_entity.split('-', 1)[1] if '-' in current_entity else current_entity
                entity_text = ''.join(current_tokens)
                if entity_type not in entities:
                    entities[entity_type] = []
                entities[entity_type].append(entity_text)
                current_entity = None
                current_tokens = []
            else:
                # 结束当前实体（如果有的话）
                if current_entity and current_tokens:
                    entity_type = current_entity.split('-', 1)[1] if '-' in current_entity else current_entity
                    entity_text = ''.join(current_tokens)
                    if entity_type not in entities:
                        entities[entity_type] = []
                    entities[entity_type].append(entity_text)
                current_entity = None
                current_tokens = []
        
        # 处理最后一个实体
        if current_entity and current_tokens:
            entity_type = current_entity.split('-', 1)[1] if '-' in current_entity else current_entity
            entity_text = ''.join(current_tokens)
            if entity_type not in entities:
                entities[entity_type] = []
            entities[entity_type].append(entity_text)
        
        return entities
    
    def format_address(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        将原始NER结果格式化为易读的地址格式
        
        Args:
            raw_data: 包含tokens, ner_tags, text的原始数据
            
        Returns:
            格式化后的地址字典
        """
        tokens = raw_data.get('tokens', [])
        ner_tags = raw_data.get('ner_tags', [])
        text = raw_data.get('text', '')
        
        # 提取实体
        entities = self.extract_entities_from_tokens(tokens, ner_tags)
        
        # 构建格式化结果
        formatted_result = {
            'original_text': text,
            'entities': {}
        }
        
        # 按优先级排序的实体类型
        priority_order = [
            'prov', 'city', 'district', 'town', 'community', 'devzone',
            'road', 'roadno', 'intersection', 'poi', 'subpoi', 
            'houseno', 'cellno', 'floorno', 'roomno', 'assist', 'distance'
        ]
        
        # 按优先级添加实体
        for entity_type in priority_order:
            if entity_type in entities:
                chinese_name = self.entity_mapping.get(entity_type, entity_type)
                # 如果有多个相同类型的实体，用逗号连接
                entity_value = ', '.join(entities[entity_type])
                formatted_result['entities'][entity_type] = entity_value
        
        # 添加其他未在优先级列表中的实体
        for entity_type, entity_list in entities.items():
            if entity_type not in priority_order:
                chinese_name = self.entity_mapping.get(entity_type, entity_type)
                entity_value = ', '.join(entity_list)
                formatted_result['entities'][entity_type] = entity_value
        
        return formatted_result
    
    def create_simple_format(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """
        创建简化的地址格式（类似你提供的示例格式）
        
        Args:
            raw_data: 包含tokens, ner_tags, text的原始数据
            
        Returns:
            简化的地址字典
        """
        tokens = raw_data.get('tokens', [])
        ner_tags = raw_data.get('ner_tags', [])
        text = raw_data.get('text', '')
        
        # 提取实体
        entities = self.extract_entities_from_tokens(tokens, ner_tags)
        
        # 构建简化结果
        simple_result = {
            'original_text': text
        }
        
        # 映射到简化字段
        field_mapping = {
            'prov': 'province',
            'city': 'city', 
            'district': 'district',
            'town': 'town',
            'community': 'community',
            'road': 'road',
            'roadno': 'road_number',
            'poi': 'poi',
            'subpoi': 'sub_poi',
            'houseno': 'house_number',
            'cellno': 'unit_number',
            'floorno': 'floor',
            'roomno': 'room_number',
            'devzone': 'development_zone',
            'intersection': 'intersection',
            'assist': 'additional_info'
        }
        
        for entity_type, entity_list in entities.items():
            field_name = field_mapping.get(entity_type, entity_type)
            simple_result[field_name] = ', '.join(entity_list) if len(entity_list) > 1 else entity_list[0]
        
        return simple_result

def convert_inference_results(input_file: str, output_file: str, format_type: str = 'detailed'):
    """
    转换推理结果文件
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        format_type: 格式类型 ('detailed' 或 'simple')
    """
    formatter = AddressFormatter()
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 {input_file} 不存在")
        return
    
    results = []
    
    # 读取原始数据
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                raw_data = json.loads(line.strip())
                
                if format_type == 'simple':
                    formatted_data = formatter.create_simple_format(raw_data)
                else:
                    formatted_data = formatter.format_address(raw_data)
                
                results.append(formatted_data)
                
            except json.JSONDecodeError as e:
                print(f"警告: 第{line_num}行JSON解析失败: {e}")
            except Exception as e:
                print(f"警告: 第{line_num}行处理失败: {e}")
    
    # 保存格式化结果
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
    
    print(f"转换完成! 共处理 {len(results)} 条记录")
    print(f"结果已保存到: {output_file}")

def main():
    """主函数"""
    input_file = "./result/inference_results.json"
    
    # 生成详细格式
    detailed_output = "./result/formatted_detailed.json"
    convert_inference_results(input_file, detailed_output, 'detailed')
    
    # # 生成简化格式
    # simple_output = "./result/formatted_simple.json"
    # convert_inference_results(input_file, simple_output, 'simple')
    
    # print("\n格式转换完成!")
    # print("详细格式:", detailed_output)
    # # print("简化格式:", simple_output)
    
    # # 显示示例结果
    # if os.path.exists(simple_output):
    #     print("\n简化格式示例:")
    #     with open(simple_output, 'r', encoding='utf-8') as f:
    #         first_result = f.readline().strip()
    #         if first_result:
    #             example = json.loads(first_result)
    #             print(json.dumps(example, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()