import gc
import torch
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

PDF_PATH = Path(__file__).parent.parent.parent / "data" / "document" / "世界冠军健身全书-177-209.pdf"
if not PDF_PATH.exists():
    raise FileNotFoundError(f"找不到源文件: {PDF_PATH}")

MD_PATH = PDF_PATH.with_suffix(".md")

if MD_PATH.exists():
    print(f"📑 发现已存在的 Markdown，跳过解析: {MD_PATH.name}")
else:
    print(f"即将解析: {PDF_PATH.name}")

    config_dict = {
        "output_format": "markdown",
        "parallel_factor": 1,           # 单并行，防爆内存
        "workers": 1,                   # 单进程
        "disable_image_extraction": True,   # 不提取图片，省内存
        "batch_multiplier": 1,          # 最小批次，显存友好
        "disable_multiprocessing": True,    # Windows 必须加，防止 spawn 进程爆内存
    }
    # 若想只转部分页，取消注释：
    # config_dict["page_range"] = "0-30"

    config = ConfigParser(config_dict)
    model_dict = create_model_dict()

    try:
        converter = PdfConverter(
            config=config.generate_config_dict(),
            artifact_dict=model_dict,
        )
        print("🚀 开始转换，请耐心等待...")
        rendered = converter(str(PDF_PATH))

        with open(MD_PATH, "w", encoding="utf-8") as f:
            f.write(rendered.markdown)
        print(f"✅ 解析成功！已保存到: {MD_PATH}")

    except Exception as e:
        print(f"❌ 解析过程中发生错误: {e}")
        raise  # 重新抛出，保留完整堆栈信息

    finally:
        # 无论成功失败都释放资源
        if 'converter' in locals():
            del converter
        if 'model_dict' in locals():
            del model_dict
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"🖥️  显存已释放，剩余占用: {torch.cuda.memory_allocated() / 1024**2:.1f} MB")
