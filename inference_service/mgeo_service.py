#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import traceback
import argparse
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# 导入我们的推理和转换模块
from inference import MGeoInference
from convert_to_11_levels import classify_elements_to_11_levels
from convert_tokens_to_entities import AddressFormatter

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 请求和响应模型
class AddressRequest(BaseModel):
    address: str
    city: Optional[str] = None
    user_id: Optional[str] = None

class TokenResult(BaseModel):
    tokens: List[str]
    ner_tags: List[str]
    text: str

class EntityResult(BaseModel):
    original_text: str
    entities: Dict[str, str]

class Level11Result(BaseModel):
    original_text: str
    level1: str = ""  # 省份
    level2: str = ""  # 城市
    level3: str = ""  # 区县
    level4: str = ""  # 乡镇
    level5: str = ""  # 道路/方向
    level6: str = ""  # 路号
    level7: str = ""  # POI/小区
    level8: str = ""  # 附加POI信息/房屋号
    level9: str = ""  # 单元号
    level10: str = "" # 楼层号
    level11: str = "" # 房间号
    remark: str = ""  # 备注

class StandardAddrResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    token_result: Optional[TokenResult] = None
    entity_result: Optional[EntityResult] = None
    level11_result: Optional[Level11Result] = None
    processing_time: Optional[float] = None

# 全局变量
app = FastAPI(
    title="MGeo地址标准化服务",
    description="基于MGeo模型的地址解析和标准化服务",
    version="1.0.0"
)

# 全局推理器和格式化器
inferencer: Optional[MGeoInference] = None
formatter: Optional[AddressFormatter] = None

# 全局配置
config = {
    "model_path": "./mgeo_trained_251024",
    "host": "0.0.0.0",
    "port": 7869
}

@app.on_event("startup")
async def startup_event():
    """服务启动时初始化模型"""
    global inferencer, formatter, config
    
    try:
        logger.info("正在初始化MGeo推理服务...")
        
        # 使用配置中的模型路径
        model_path = config["model_path"]
        logger.info(f"使用模型路径: {model_path}")
        
        if not os.path.exists(model_path):
            logger.error(f"模型路径不存在: {model_path}")
            raise Exception(f"模型路径不存在: {model_path}")
        
        # 初始化推理器
        logger.info("正在加载MGeo模型...")
        inferencer = MGeoInference(model_path)
        logger.info("MGeo模型加载完成")
        
        # 初始化格式化器
        formatter = AddressFormatter()
        logger.info("地址格式化器初始化完成")
        
        logger.info("MGeo推理服务启动成功!")
        
    except Exception as e:
        logger.error(f"服务启动失败: {e}")
        logger.error(traceback.format_exc())
        raise

@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "MGeo地址标准化服务",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "standardaddr": "/standardaddr - 地址标准化接口",
            "health": "/health - 健康检查",
            "docs": "/docs - API文档"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    global inferencer, formatter
    
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": inferencer is not None,
        "formatter_loaded": formatter is not None
    }
    
    if not inferencer or not formatter:
        status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail="服务未就绪")
    
    return status

@app.post("/standardaddr", response_model=StandardAddrResponse)
async def standardize_address(request: AddressRequest):
    """
    地址标准化接口
    
    Args:
        request: 包含地址信息的请求
        
    Returns:
        标准化后的地址信息，包含token级别、实体级别和11级分类结果
    """
    global inferencer, formatter
    
    start_time = datetime.now()
    
    try:
        # 检查服务状态
        if not inferencer or not formatter:
            raise HTTPException(
                status_code=503, 
                detail="推理服务未就绪，请稍后重试"
            )
        
        address = request.address.strip()
        if not address:
            raise HTTPException(
                status_code=400,
                detail="地址不能为空"
            )
        
        logger.info(f"处理地址标准化请求: {address}")
        
        # 步骤1: 使用inference进行token级别推理
        logger.info("步骤1: 进行token级别推理...")
        token_prediction = inferencer.predict_single(address)
        
        token_result = TokenResult(
            tokens=token_prediction['tokens'],
            ner_tags=token_prediction['ner_tags'],
            text=token_prediction['text']
        )
        
        # 步骤2: 转换为实体格式
        logger.info("步骤2: 转换为实体格式...")
        entity_formatted = formatter.format_address(token_prediction)
        
        entity_result = EntityResult(
            original_text=entity_formatted['original_text'],
            entities=entity_formatted['entities']
        )
        
        # 步骤3: 转换为11级分类
        logger.info("步骤3: 转换为11级分类...")
        level11_data = classify_elements_to_11_levels(
            entity_formatted['entities'], 
            address
        )
        
        level11_result = Level11Result(
            original_text=level11_data.get('original_text', address),
            level1=level11_data.get('level1', ''),
            level2=level11_data.get('level2', ''),
            level3=level11_data.get('level3', ''),
            level4=level11_data.get('level4', ''),
            level5=level11_data.get('level5', ''),
            level6=level11_data.get('level6', ''),
            level7=level11_data.get('level7', ''),
            level8=level11_data.get('level8', ''),
            level9=level11_data.get('level9', ''),
            level10=level11_data.get('level10', ''),
            level11=level11_data.get('level11', ''),
            remark=level11_data.get('remark', '')
        )
        
        # 计算处理时间
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 构建响应数据
        response_data = {
            "address": address,
            "city": request.city,
            "user_id": request.user_id,
            "entities": entity_formatted['entities'],
            "levels": {
                "level1": level11_result.level1,
                "level2": level11_result.level2,
                "level3": level11_result.level3,
                "level4": level11_result.level4,
                "level5": level11_result.level5,
                "level6": level11_result.level6,
                "level7": level11_result.level7,
                "level8": level11_result.level8,
                "level9": level11_result.level9,
                "level10": level11_result.level10,
                "level11": level11_result.level11,
                "remark": level11_result.remark
            }
        }
        
        logger.info(f"地址标准化完成，耗时: {processing_time:.3f}秒")
        
        return StandardAddrResponse(
            success=True,
            message="地址标准化成功",
            data=response_data,
            token_result=token_result,
            entity_result=entity_result,
            level11_result=level11_result,
            processing_time=processing_time
        )
        
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"地址标准化失败: {e}")
        logger.error(traceback.format_exc())
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return StandardAddrResponse(
            success=False,
            message=f"地址标准化失败: {str(e)}",
            processing_time=processing_time
        )

@app.post("/inference", response_model=Dict[str, Any])
async def inference_only(request: AddressRequest):
    """
    仅进行推理，返回token级别结果
    """
    global inferencer
    
    try:
        if not inferencer:
            raise HTTPException(status_code=503, detail="推理服务未就绪")
        
        address = request.address.strip()
        if not address:
            raise HTTPException(status_code=400, detail="地址不能为空")
        
        result = inferencer.predict_single(address)
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        logger.error(f"推理失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

@app.post("/batch_standardaddr")
async def batch_standardize_address(addresses: List[str]):
    """
    批量地址标准化接口
    """
    global inferencer, formatter
    
    try:
        if not inferencer or not formatter:
            raise HTTPException(status_code=503, detail="推理服务未就绪")
        
        if not addresses:
            raise HTTPException(status_code=400, detail="地址列表不能为空")
        
        results = []
        
        for address in addresses:
            try:
                # Token级别推理
                token_prediction = inferencer.predict_single(address)
                
                # 转换为实体格式
                entity_formatted = formatter.format_address(token_prediction)
                
                # 转换为11级分类
                level11_data = classify_elements_to_11_levels(
                    entity_formatted['entities'], 
                    address
                )
                
                results.append({
                    "address": address,
                    "success": True,
                    "entities": entity_formatted['entities'],
                    "levels": level11_data
                })
                
            except Exception as e:
                logger.error(f"处理地址失败 {address}: {e}")
                results.append({
                    "address": address,
                    "success": False,
                    "error": str(e)
                })
        
        return {
            "success": True,
            "total": len(addresses),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"批量处理失败: {e}")
        return {
            "success": False,
            "message": str(e)
        }

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="MGeo地址标准化服务")
    
    parser.add_argument(
        "--model-path", "-m",
        type=str,
        default="./mgeo_trained_251024",
        help="模型文件路径 (默认: ./mgeo_trained_251024)"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="服务监听地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=7869,
        help="服务监听端口 (默认: 7869)"
    )
    
    parser.add_argument(
        "--reload",
        action="store_true",
        help="启用热重载 (开发模式)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        default="info",
        choices=["debug", "info", "warning", "error"],
        help="日志级别 (默认: info)"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 更新全局配置
    config.update({
        "model_path": args.model_path,
        "host": args.host,
        "port": args.port
    })
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    print(f"启动MGeo推理服务...")
    print(f"模型路径: {config['model_path']}")
    print(f"服务地址: {config['host']}:{config['port']}")
    print(f"日志级别: {args.log_level}")
    
    # 启动服务
    uvicorn.run(
        "mgeo_service:app",
        host=config["host"],
        port=config["port"],
        reload=args.reload,
        log_level=args.log_level
    )