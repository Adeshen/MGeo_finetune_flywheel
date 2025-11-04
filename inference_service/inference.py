import os
import json
import torch
from modelscope.models import Model
from modelscope.preprocessors import TokenClassificationTransformersPreprocessor
from modelscope.pipelines import pipeline
import pandas as pd

class MGeoInference:
    def __init__(self, model_path, label_list=None):
        """
        初始化推理器
        
        Args:
            model_path: 训练好的模型路径
            label_list: 标签列表，如果为None则从配置文件中获取
        """
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # 初始化属性
        self.model = None
        self.preprocessor = None
        self.nlp = None
        
        # 加载标签映射
        self.id2label, self.label2id = self._load_label_mapping()
        
        # 尝试加载模型
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        try:
            # 尝试使用pipeline方式加载
            print("尝试使用Pipeline加载...")
            self.nlp = pipeline(
                task='token-classification',
                model=self.model_path,
                device=0 if torch.cuda.is_available() else -1
            )
            print("Pipeline加载成功")
        except Exception as e:
            print(f"Pipeline加载失败: {e}")
            try:
                # 直接加载模型和预处理器
                print("尝试直接加载模型...")
                self.model = Model.from_pretrained(self.model_path)
                self.preprocessor = TokenClassificationTransformersPreprocessor(
                    model_dir=self.model_path
                )
                print("模型直接加载成功")
            except Exception as e2:
                print(f"直接加载模型也失败: {e2}")
                raise Exception(f"无法加载模型: Pipeline失败({e}), 直接加载失败({e2})")
    
    def _load_label_mapping(self):
        """从配置文件加载标签映射"""
        config_path = os.path.join(self.model_path, 'configuration.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                id2label = config['model']['id2label']
                label2id = config['model']['label2id']
                return id2label, label2id
        else:
            # 默认标签映射
            return self._get_default_label_mapping()
    
    def _get_default_label_mapping(self):
        """获取默认标签映射"""
        labels = [
            'B-assist', 'B-cellno', 'B-city', 'B-community', 'B-devzone', 'B-distance',
            'B-district', 'B-floorno', 'B-houseno', 'B-intersection', 'B-poi', 'B-prov',
            'B-road', 'B-roadno', 'B-roomno', 'B-subpoi', 'B-town', 'B-village_group',
            'E-assist', 'E-cellno', 'E-city', 'E-community', 'E-devzone', 'E-distance',
            'E-district', 'E-floorno', 'E-houseno', 'E-intersection', 'E-poi', 'E-prov',
            'E-road', 'E-roadno', 'E-roomno', 'E-subpoi', 'E-town', 'E-village_group',
            'I-assist', 'I-cellno', 'I-city', 'I-community', 'I-devzone', 'I-distance',
            'I-district', 'I-floorno', 'I-houseno', 'I-intersection', 'I-poi', 'I-prov',
            'I-road', 'I-roadno', 'I-roomno', 'I-subpoi', 'I-town', 'I-village_group',
            'O', 'S-assist', 'S-community', 'S-district', 'S-intersection', 'S-poi', 'S-roomno'
        ]
        
        id2label = {str(i): label for i, label in enumerate(labels)}
        label2id = {label: i for i, label in enumerate(labels)}
        return id2label, label2id
    
    def predict_single(self, text):
        """
        对单个文本进行预测
        
        Args:
            text: 输入的地址文本
            
        Returns:
            dict: 包含tokens和预测标签的字典
        """
        # 将文本转换为字符列表
        tokens = list(text)
        
        if self.nlp is not None:
            # 使用pipeline进行预测
            try:
                results = self.nlp(text)
                # 检查结果格式
                if isinstance(results, str):
                    print(f"Pipeline返回字符串: {results}")
                    return self._predict_with_model(text)
                elif isinstance(results, dict):
                    # 如果返回字典，尝试提取output字段
                    if 'output' in results:
                        results = results['output']
                    else:
                        print(f"Pipeline返回字典但无output字段: {results}")
                        return self._predict_with_model(text)
                
                return self._process_pipeline_results(text, results)
            except Exception as e:
                print(f"Pipeline预测失败: {e}")
                return self._predict_with_model(text)
        else:
            return self._predict_with_model(text)
    
    def _predict_with_model(self, text):
        """使用模型直接预测"""
        if self.model is None or self.preprocessor is None:
            raise Exception("模型或预处理器未正确加载")
            
        tokens = list(text)
        
        try:
            # 预处理输入
            model_inputs = self.preprocessor(text)
            model_inputs_copy = dict(model_inputs)
            model_inputs_copy.pop('text', None)
            
            # 模型推理
            with torch.no_grad():
                outputs = self.model(**model_inputs_copy)
            
            # 获取预测结果
            predictions = torch.argmax(outputs.logits, dim=-1)
            
            # 转换为标签
            ner_tags = []
            for pred_ids in predictions[0]:  # 取第一个样本
                if pred_ids.item() < len(self.id2label):
                    ner_tags.append(self.id2label[str(pred_ids.item())])
                else:
                    ner_tags.append('O')
            
            # 截断到与tokens相同长度
            ner_tags = ner_tags[:len(tokens)]
            # 如果长度不够，补充'O'标签
            while len(ner_tags) < len(tokens):
                ner_tags.append('O')
            
            return {
                'tokens': tokens,
                'ner_tags': ner_tags,
                'text': text
            }
        except Exception as e:
            print(f"模型预测失败: {e}")
            # 返回默认结果
            return {
                'tokens': tokens,
                'ner_tags': ['O'] * len(tokens),
                'text': text
            }
    
    def _process_pipeline_results(self, text, results):
        """处理pipeline结果"""
        tokens = list(text)
        ner_tags = ['O'] * len(tokens)
        
        if not isinstance(results, list):
            print(f"Pipeline结果格式错误: {type(results)}, {results}")
            return {
                'tokens': tokens,
                'ner_tags': ner_tags,
                'text': text
            }
        
        for result in results:
            if not isinstance(result, dict):
                continue
                
            # 兼容不同的字段名
            start = result.get('start', result.get('span_start', 0))
            end = result.get('end', result.get('span_end', len(text)))
            label = result.get('entity_group', result.get('entity', result.get('type', 'O')))
            
            # 确保索引在有效范围内
            start = max(0, min(start, len(tokens)))
            end = max(start, min(end, len(tokens)))
            
            # 将预测结果映射到字符级别的标签
            for i in range(start, end):
                if i == start:
                    if not label.startswith(('B-', 'I-', 'E-', 'S-')):
                        ner_tags[i] = f'B-{label}'
                    else:
                        ner_tags[i] = label
                else:
                    base_label = label[2:] if label.startswith(('B-', 'I-', 'E-', 'S-')) else label
                    ner_tags[i] = f'I-{base_label}'
        
        return {
            'tokens': tokens,
            'ner_tags': ner_tags,
            'text': text
        }
    
    def predict_batch(self, texts):
        """
        批量预测
        
        Args:
            texts: 文本列表
            
        Returns:
            list: 预测结果列表
        """
        results = []
        for text in texts:
            result = self.predict_single(text)
            results.append(result)
        return results
    
    def extract_entities(self, text):
        """
        提取实体并按类型分组
        
        Args:
            text: 输入文本
            
        Returns:
            dict: 按实体类型分组的实体字典
        """
        prediction = self.predict_single(text)
        tokens = prediction['tokens']
        ner_tags = prediction['ner_tags']
        
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
    
    def save_predictions(self, texts, output_file):
        """
        保存预测结果到文件
        
        Args:
            texts: 输入文本列表
            output_file: 输出文件路径
        """
        predictions = self.predict_batch(texts)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for pred in predictions:
                f.write(json.dumps(pred, ensure_ascii=False) + '\n')
        
        print(f"预测结果已保存到: {output_file}")


def main():
    # 模型路径
    model_path = "mgeo_trained_251024"
    
    # 检查模型是否存在
    if not os.path.exists(model_path):
        print(f"错误: 模型路径 {model_path} 不存在")
        print("请先运行训练脚本生成模型")
        return
    
    # 初始化推理器
    print("正在加载模型...")
    try:
        inferencer = MGeoInference(model_path)
        print("模型加载完成!")
    except Exception as e:
        print(f"模型加载失败: {e}")
        return
    
    # 测试样例
    test_texts = [
        "浙江杭州市江干区九堡镇三村村一区1190房",
        "浙江省温州市平阳县海西镇宋埠公园南路0000号",
        "上海市徐汇区宛平南路000弄0号楼佳安公寓",
        "北京市朝阳区建国门外大街1号国贸大厦A座20层",
        "广东省广州市天河区珠村北社大街八巷7号1楼",
        "广州市南沙区南沙街道环市大道中无门牌号越秀滨海新城三期33栋一单元8层801",
        "(二湾FTTH)广州市番禺区大岗镇怡乐园南6街1号,联系电话13711002192",
        "番禺区钟村街道市广路8号祈福新村C区九街98号301"
    ]
    output_file = "./result/inference_results.json"
    # 从CSV文件读取测试样例
    # inference_file = pd.read_excel("./data/珠村/珠村重跑结果.xlsx")
    # test_texts = inference_file['address'].tolist()

    print("\n开始推理测试:")
    print("=" * 50)
    
    # for i, text in enumerate(test_texts, 1):
    #     print(f"\n测试样例 {i}: {text}")
        
    #     try:
    #         # 获取预测结果
    #         prediction = inferencer.predict_single(text)
    #         print("Token级别预测:")
    #         print(prediction)
    #         # for token, tag in zip(prediction['tokens'], prediction['ner_tags']):
    #         #     if tag != 'O':  # 只显示非O标签
    #         #         print(f"  {token}: {tag}")
            
    #         # 提取实体
    #         entities = inferencer.extract_entities(text)
    #         print("提取的实体:")
    #         for entity_type, entity_list in entities.items():
    #             print(f"  {entity_type}: {entity_list}")
                
    #     except Exception as e:
    #         print(f"预测失败: {e}")
    #         import traceback
    #         traceback.print_exc()
        
    #     print("-" * 30)
    
    # # 批量预测示例
    # print("\n批量预测测试:")
    try:
        batch_results = inferencer.predict_batch(test_texts)
        
        # 保存结果
        os.makedirs("./result", exist_ok=True)
        inferencer.save_predictions(test_texts, output_file)
        
        print(f"\n推理完成! 结果已保存到 {output_file}")
    except Exception as e:
        print(f"批量预测失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()