import json
import time
import os
from typing import List, Dict, Any, Optional
import argparse
from tqdm import tqdm
import openai
from dotenv import load_dotenv

class OpenAIAddressTagger:
    def __init__(self, delay: float = 0.5):
        """
        初始化 OpenAI 地址打标器
        
        Args:
            model: 使用的 OpenAI 模型
            delay: 请求间隔时间（秒）
        """
        # 加载环境变量
        load_dotenv()
        
        # 初始化 OpenAI 客户端
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE_URL"),
        )
        
        self.model = os.getenv("OPENAI_API_MODEL")
        self.delay = delay
        self.prompt_template = self._load_prompt_template()
        
    def _load_prompt_template(self) -> str:
        """加载提示词模板"""
        prompt_file = os.path.join(os.path.dirname(__file__), "prompt", "address_entity_tag_prompt.md")
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"警告: 未找到提示词文件 {prompt_file}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """获取默认提示词"""
        return """你是一个地址解析专家。请将给定的中文地址分解为以下类别标签：

# 行政区划类
prov（省级）、city（地级）、district（县级）、town（乡级）

# 道路地址类  
road（道路）、roadno（门牌）

# 建筑点位类
poi（兴趣点）、subpoi（子兴趣点）、houseno（楼号）、cellno（单元）、floorno（楼层）、roomno（房间号）

# 其他类
community（社区）、village_group（村组）、devzone（开发区）、assist（辅助信息）

输出要求：
- 输出JSON格式，包含所有识别出的类别-值对
- 如果地址中没有某个类别的部分，则跳过该类别

现在，请对以下地址进行分类：
{{address}}"""

    def tag_single_address(self, address: str) -> Dict[str, Any]:
        """
        对单个地址进行打标
        
        Args:
            address: 地址字符串
            
        Returns:
            包含原始地址和打标结果的字典
        """
        result = {
            "address": address,
            "success": False,
            "entities": None,
            "error": None,
            "raw_response": None
        }
        
        try:
            # 准备提示词
            prompt = self.prompt_template.replace("{{address}}", address)
            
            # 调用 OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 降低随机性
                max_tokens=1000
            )
            
            
            # 提取响应内容
            raw_response = response.choices[0].message.content.strip()
            result["raw_response"] = raw_response
            
            # 解析 JSON 结果
            entities = self._parse_json_response(raw_response)
            
            if entities:
                result["success"] = True
                result["entities"] = entities
            else:
                result["error"] = "JSON 解析失败"
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
    
    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 JSON 响应"""
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # 尝试提取 markdown 中的 JSON
                if "```json" in response:
                    json_start = response.find("```json") + 7
                    json_end = response.find("```", json_start)
                    json_str = response[json_start:json_end].strip()
                    return json.loads(json_str)
                elif "```" in response:
                    # 尝试提取任何代码块
                    json_start = response.find("```") + 3
                    json_end = response.find("```", json_start)
                    json_str = response[json_start:json_end].strip()
                    return json.loads(json_str)
                else:
                    # 尝试提取 { } 之间的内容
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    if start != -1 and end > start:
                        json_str = response[start:end]
                        return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        return None
    
    def batch_tag_addresses(self, addresses: List[str], output_file: str, 
                           progress_file: Optional[str] = None) -> None:
        """
        批量处理地址列表
        
        Args:
            addresses: 地址列表
            output_file: 输出文件路径
            progress_file: 进度保存文件路径
        """
        print(f"开始批量处理 {len(addresses)} 个地址...")
        
        # 检查是否有进度文件
        start_index = 0
        if progress_file and os.path.exists(progress_file):
            with open(progress_file, 'r') as f:
                start_index = int(f.read().strip())
            print(f"从第 {start_index + 1} 个地址继续处理...")
        
        # 打开输出文件（追加模式）
        mode = 'a' if start_index > 0 else 'w'
        with open(output_file, mode, encoding='utf-8') as f:
            for i, address in enumerate(tqdm(addresses[start_index:], 
                                           initial=start_index, 
                                           total=len(addresses),
                                           desc="处理地址")):
                
                current_index = start_index + i
                
                # 处理地址
                result = self.tag_single_address(address)
                
                # 写入结果
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
                f.flush()  # 确保立即写入
                
                # 更新进度
                if progress_file:
                    with open(progress_file, 'w') as pf:
                        pf.write(str(current_index + 1))
                
                # 延时
                if self.delay > 0:
                    time.sleep(self.delay)
        
        # 清理进度文件
        if progress_file and os.path.exists(progress_file):
            os.remove(progress_file)
        
        print(f"批量处理完成！结果保存到: {output_file}")
    
    def tag_addresses_from_file(self, input_file: str, output_file: str, 
                               address_key: str = "address") -> None:
        """
        从文件读取地址并进行批量打标
        
        Args:
            input_file: 输入文件路径（支持 .jsonl 和 .json）
            output_file: 输出文件路径
            address_key: 地址字段的键名
        """
        addresses = self._load_addresses_from_file(input_file, address_key)
        progress_file = f"{output_file}.progress"
        self.batch_tag_addresses(addresses, output_file, progress_file)
    
    def _load_addresses_from_file(self, input_file: str, address_key: str) -> List[str]:
        """从文件加载地址列表"""
        addresses = []
        
        if input_file.endswith('.jsonl'):
            # JSONL 格式
            with open(input_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())
                        if address_key in data:
                            addresses.append(data[address_key])
                        else:
                            print(f"警告: 第 {line_num} 行缺少 '{address_key}' 字段")
                    except json.JSONDecodeError as e:
                        print(f"警告: 第 {line_num} 行 JSON 解析错误: {e}")
        
        elif input_file.endswith('.json'):
            # JSON 格式
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and address_key in item:
                            addresses.append(item[address_key])
                        elif isinstance(item, str):
                            addresses.append(item)
                elif isinstance(data, dict) and address_key in data:
                    addresses.append(data[address_key])
        
        else:
            # 纯文本格式，每行一个地址
            with open(input_file, 'r', encoding='utf-8') as f:
                addresses = [line.strip() for line in f if line.strip()]
        
        print(f"从 {input_file} 加载了 {len(addresses)} 个地址")
        return addresses

def main():
    parser = argparse.ArgumentParser(description="使用 OpenAI 进行地址实体标注")
    parser.add_argument("--input", "-i", required=True, help="输入文件路径")
    parser.add_argument("--output", "-o", required=True, help="输出文件路径")
    parser.add_argument("--address-key", default="address", help="地址字段键名（默认: address）")
    parser.add_argument("--delay", type=float, default=0.5, help="请求间隔时间（秒，默认: 0.5）")
    
    args = parser.parse_args()
    
    # 创建打标器
    tagger = OpenAIAddressTagger(delay=args.delay)
    
    # 执行批量打标
    tagger.tag_addresses_from_file(args.input, args.output, args.address_key)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) == 1:
        # 示例模式
        print("运行示例模式...")
        
        # 示例地址
        sample_addresses = [
            "广东省广州市天河区珠村北社大街八巷7号1楼",
            "浙江省杭州市西湖区文三路",
            "广州市南沙区南沙街道环市大道中无门牌号越秀滨海新城三期33栋一单元8层801",
            "番禺区钟村街道市广路8号祈福新村C区九街98号301"
        ]
        
        # 创建打标器
        tagger = OpenAIAddressTagger(delay=1.0)  # 示例模式使用较长延时
        
        # 输出文件
        output_file = "openai_sample_results.jsonl"
        
        # 批量处理
        tagger.batch_tag_addresses(sample_addresses, output_file)
        
        # 显示结果预览
        print(f"\n示例处理完成！查看结果文件: {output_file}")
        print("\n结果预览:")
        print("=" * 80)
        
        with open(output_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                result = json.loads(line)
                print(f"\n地址 {i+1}: {result['address']}")
                print(f"成功: {result['success']}")
                
                if result['success']:
                    print("实体标注:")
                    for key, value in result['entities'].items():
                        print(f"  {key}: {value}")
                else:
                    print(f"错误: {result['error']}")
                    if result.get('raw_response'):
                        print(f"原始响应: {result['raw_response'][:100]}...")
                
                print("-" * 60)
    else:
        # 命令行模式
        main()