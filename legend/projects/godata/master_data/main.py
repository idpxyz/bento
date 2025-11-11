from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from interface.api.dizhi_api import router as dizhi_router
from interface.api.tiangan_api import router as tiangan_router

# 创建FastAPI应用实例
app = FastAPI(
    title="天干地支管理系统",
    description="基于DDD和SOLID原则设计的中国传统历法管理系统，支持天干地支的六合、六冲、三合等关系",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tiangan_router)
app.include_router(dizhi_router)


@app.get("/")
async def root():
    """根路径 - 返回系统信息"""
    return {
        "message": "天干地支管理系统",
        "version": "1.0.0",
        "architecture": "DDD + SOLID + FastAPI",
        "description": "基于领域驱动设计和SOLID原则构建的中国传统历法管理系统",
        "features": [
            "天干管理 - 支持合化关系",
            "地支管理 - 支持六合、六冲、三合关系",
            "完整的业务规则验证",
            "RESTful API接口"
        ],
        "endpoints": {
            "天干": "/tiangan",
            "地支": "/dizhi",
            "API文档": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "message": "系统运行正常"}


@app.get("/api-info")
async def api_info():
    """API信息端点"""
    return {
        "天干功能": {
            "基础查询": [
                "GET /tiangan/ - 获取所有天干",
                "GET /tiangan/{name} - 根据名称获取天干",
                "GET /tiangan/order/{order} - 根据序号获取天干",
                "GET /tiangan/wuxing/{wu_xing} - 根据五行获取天干",
                "GET /tiangan/yin-yang/{yin_yang} - 根据阴阳获取天干"
            ],
            "合化关系": [
                "POST /tiangan/combination - 检查天干合化",
                "GET /tiangan/{name}/compatible - 获取相合天干",
                "GET /tiangan/{name}/next/{steps} - 获取指定步数后的天干"
            ]
        },
        "地支功能": {
            "基础查询": [
                "GET /dizhi/ - 获取所有地支",
                "GET /dizhi/{name} - 根据名称获取地支",
                "GET /dizhi/order/{order} - 根据序号获取地支",
                "GET /dizhi/wuxing/{wu_xing} - 根据五行获取地支",
                "GET /dizhi/yin-yang/{yin_yang} - 根据阴阳获取地支",
                "GET /dizhi/animal/{animal} - 根据生肖获取地支"
            ],
            "六合关系": [
                "POST /dizhi/liu-he - 检查地支六合",
                "GET /dizhi/{name}/liu-he - 获取六合伙伴"
            ],
            "六冲关系": [
                "POST /dizhi/liu-chong - 检查地支六冲",
                "GET /dizhi/{name}/liu-chong - 获取六冲伙伴"
            ],
            "三合关系": [
                "POST /dizhi/san-he - 检查地支三合",
                "POST /dizhi/san-he-group - 创建三合局",
                "GET /dizhi/{name}/san-he - 获取三合伙伴",
                "GET /dizhi/san-he-groups/all - 获取所有三合局"
            ],
            "综合查询": [
                "GET /dizhi/{name}/relationships - 获取所有关系",
                "GET /dizhi/{name}/next/{steps} - 获取指定步数后的地支"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True)
