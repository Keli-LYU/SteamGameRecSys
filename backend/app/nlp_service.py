"""
NLP Sentiment Analysis Service
NLP情感分析服务 - 使用BERT模型进行文本情感分类

核心功能:
1. 加载 HuggingFace 预训练BERT模型 (distilbert-base-uncased-finetuned-sst-2-english)
2. 提供 predict_sentiment() 函数进行情感推理
3. 使用单例模式避免重复加载模型 (节省内存和启动时间)

资源管理:
- 模型大小: ~250MB
- 内存占用: ~500MB (推理时)
- 建议Kubernetes资源限制: 1.5-2GB RAM
"""
from transformers import pipeline
from typing import Dict
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    情感分析器单例类
    - 在首次调用时加载BERT模型
    - 后续调用复用已加载的模型
    """
    _instance = None
    _model = None
    
    def __new__(cls):
        """单例模式 - 确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super(SentimentAnalyzer, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化模型 (仅在首次创建时执行)"""
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """
        加载BERT情感分析模型
        
        模型选择: distilbert-base-uncased-finetuned-sst-2-english
        - 优点: 轻量级 (66M参数 vs BERT的110M)
        - 训练数据: Stanford Sentiment Treebank (SST-2)
        - 输出: POSITIVE / NEGATIVE (二分类)
        
        注意: 首次运行时会从HuggingFace Hub下载模型缓存到 ~/.cache/huggingface/
        在Docker镜像中建议预下载模型以加速启动
        """
        try:
            logger.info("Loading BERT sentiment analysis model...")
            
            # 使用HuggingFace pipeline简化推理流程
            # task="sentiment-analysis" 会自动处理tokenization和post-processing
            self._model = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=-1  # -1表示使用CPU (在K8s中GPU支持需额外配置)
            )
            
            logger.info("Model loaded successfully!")
            logger.info(f"Model: {self._model.model.config._name_or_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def predict(self, text: str) -> Dict[str, any]:
        """
        执行情感预测
        
        Args:
            text (str): 待分析的文本 (最大512 tokens,超出会被截断)
        
        Returns:
            Dict: {
                "label": "POSITIVE" or "NEGATIVE",
                "confidence": 0.0-1.0 (模型置信度)
            }
        
        示例:
            >>> analyzer = SentimentAnalyzer()
            >>> result = analyzer.predict("This game is amazing!")
            >>> print(result)
            {'label': 'POSITIVE', 'score': 0.9998}
        """
        if self._model is None:
            raise RuntimeError("Model not initialized")
        
        try:
            # 执行推理
            # pipeline会自动处理: tokenization -> model forward -> softmax -> argmax
            result = self._model(text[:512])[0]  # 限制最大长度512 tokens
            
            return {
                "label": result["label"],      # POSITIVE 或 NEGATIVE
                "confidence": result["score"]  # 置信度分数
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            raise RuntimeError(f"Sentiment prediction error: {e}")


# ============================================
# 全局单例实例 - 在应用启动时初始化
# ============================================
# 创建全局分析器实例
# 注意: 首次导入此模块时会触发模型加载,可能需要5-10秒
sentiment_analyzer = SentimentAnalyzer()


def predict_sentiment(text: str) -> Dict[str, any]:
    """
    便捷函数 - 执行情感分析
    
    这是主要的API接口函数,在FastAPI路由中调用
    
    Args:
        text (str): 待分析的文本
    
    Returns:
        Dict: {"label": str, "confidence": float}
    
    Raises:
        RuntimeError: 模型未加载或推理失败
    """
    return sentiment_analyzer.predict(text)


# ============================================
# 模型预热 (可选)
# ============================================
def warmup_model():
    """
    模型预热函数
    - 在应用启动时调用,执行一次测试推理
    - 加载模型权重到内存,避免首次API调用延迟
    """
    logger.info("Warming up BERT model...")
    try:
        result = predict_sentiment("Test sentence for model warmup")
        logger.info(f"Model warmup complete: {result}")
    except Exception as e:
        logger.warning(f"Model warmup failed: {e}")
