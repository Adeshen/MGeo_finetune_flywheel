import json
import os
import sys
import argparse
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from tqdm import tqdm

# 动态导入 finetune/new_local_mgeo_tag.py 的客户端
CURRENT_DIR = os.path.dirname(__file__)
FINETUNE_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "finetune"))
if FINETUNE_DIR not in sys.path:
    sys.path.append(FINETUNE_DIR)

try:
    from new_local_mgeo_tag import post_standardaddr as mgeo_post
except Exception as e:
    print(f"无法导入 new_local_mgeo_tag.post_standardaddr: {e}")
    mgeo_post = None


def ensure_dir(path: str):
    """确保目录存在"""
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def resolve_mgeo_url(cli_url: Optional[str]) -> List[str]:
    """确定 MGeo 服务 URL 列表（按优先级尝试）"""
    urls = []
    if cli_url:
        urls.append(cli_url)
    env_url = os.environ.get("MGEO_URL")
    if env_url:
        urls.append(env_url)

    # 默认端口优先 7869
    urls.append("http://localhost:7869/standardaddr")
    
    # 去重保持顺序
    seen = set()
    ordered = []
    for u in urls:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered


def post_with_fallback(data: Dict[str, Any], candidate_urls: List[str], timeout: int = 30) -> Optional[Dict[str, Any]]:
    """依次尝试多个 URL 直到成功"""
    if mgeo_post is None:
        print("post_standardaddr 未就绪，无法请求 MGeo 服务。")
        return None

    for u in candidate_urls:
        try:
            resp = mgeo_post(data, url=u, timeout=timeout)
            if resp is not None:
                return resp
        except Exception as e:
            print(f"请求 {u} 失败: {e}")
    return None


def batch_request_mgeo(input_file: str, output_dir: str, mgeo_url: Optional[str], 
                      limit: Optional[int] = None, sleep_sec: float = 0.0) -> str:
    """批量请求 MGeo 服务并保存原始响应"""
    ensure_dir(output_dir)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    response_file = os.path.join(output_dir, f"{base_name}_mgeo_responses_{ts}.jsonl")

    candidate_urls = resolve_mgeo_url(mgeo_url)
    print(f"MGeo 服务 URL 候选列表: {candidate_urls}")

    stats = {
        "total": 0,
        "requests_success": 0,
        "requests_failed": 0
    }

    with open(input_file, "r", encoding="utf-8") as fin, \
         open(response_file, "w", encoding="utf-8") as fout:
        
        for line_num, line in tqdm(enumerate(fin, 1), desc="批量请求MGeo"):
            if limit and stats["total"] >= limit:
                break

            line = line.strip()
            if not line:
                continue

            stats["total"] += 1

            try:
                data = json.loads(line)
            except Exception as e:
                # 保存解析错误的记录
                error_record = {
                    "line_num": line_num,
                    "address": "",
                    "orig_entities": {},
                    "mgeo_response": None,
                    "error": f"JSON解析失败: {e}",
                    "raw_line": line
                }
                fout.write(json.dumps(error_record, ensure_ascii=False) + "\n")
                stats["requests_failed"] += 1
                continue

            address = data.get("address", "")
            orig_entities = data.get("entities", {})

            # 构造请求数据
            req_data = {
                "address": address,
                "city": "广州",
                "user_id": "batch_request"
            }

            # 请求 MGeo 服务
            mgeo_response = post_with_fallback(req_data, candidate_urls, timeout=30)

            # 保存完整记录（包括原始数据和MGeo响应）
            record = {
                "line_num": line_num,
                "address": address,
                "orig_entities": orig_entities,
                "mgeo_response": mgeo_response,
                "error": None if mgeo_response else "MGeo请求失败"
            }

            if mgeo_response:
                stats["requests_success"] += 1
            else:
                stats["requests_failed"] += 1

            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

            # 休眠控制请求频率
            if sleep_sec > 0:
                time.sleep(sleep_sec)

            # 进度提示
            if stats["total"] % 100 == 0:
                success_rate = (stats["requests_success"] / stats["total"]) * 100
                print(f"[进度] 已处理 {stats['total']} 行，成功 {stats['requests_success']} 条 ({success_rate:.1f}%)")

    # 输出最终统计
    success_rate = (stats["requests_success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
    print(f"\n批量请求完成:")
    print(f"  总计: {stats['total']} 条")
    print(f"  成功: {stats['requests_success']} 条 ({success_rate:.1f}%)")
    print(f"  失败: {stats['requests_failed']} 条")
    print(f"  响应文件: {response_file}")

    return response_file


def main():
    parser = argparse.ArgumentParser(description="批量请求 MGeo 服务并保存原始响应")
    parser.add_argument("--input", required=True, help="输入 JSONL 文件路径（每行包含 address 与 entities）")
    parser.add_argument("--output_dir", default=os.path.join(CURRENT_DIR, "results"), 
                       help="输出目录（默认 code/eval/results）")
    parser.add_argument("--mgeo_url", default=None, 
                       help="MGeo服务URL（默认依次尝试环境变量、7869端口）")
    parser.add_argument("--limit", type=int, default=None, help="最多处理的行数（默认全部）")
    parser.add_argument("--sleep", type=float, default=0.1, 
                       help="每条请求后sleep秒数（默认0.1秒，避免过载）")
    
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        return

    batch_request_mgeo(
        input_file=args.input,
        output_dir=args.output_dir,
        mgeo_url=args.mgeo_url,
        limit=args.limit,
        sleep_sec=args.sleep
    )


if __name__ == "__main__":
    main()