"""
测试FastAPI是否可以正常导入和使用
"""
try:
    from fastapi import FastAPI
    print("FastAPI导入成功")
    
    # 创建一个简单的FastAPI应用
    app = FastAPI()
    print("FastAPI应用创建成功")
    
    @app.get("/")
    async def root():
        return {"message": "Hello World"}
    
    print("路由注册成功")
    print("FastAPI测试通过!")
    
except ImportError as e:
    print(f"导入错误: {e}")
except Exception as e:
    print(f"其他错误: {e}")
    import traceback
    traceback.print_exc()