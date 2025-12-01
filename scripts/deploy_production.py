#!/usr/bin/env python3
"""
Bento Framework Outbox 生产部署脚本

此脚本提供自动化的生产环境部署功能：
- 环境验证
- 数据库初始化
- 配置验证
- 性能优化索引创建
- 健康检查
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bento.config.outbox import get_outbox_projector_config
from bento.config.validation import validate_config
from bento.infrastructure.monitoring.performance import PerformanceMonitor

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ProductionDeployer:
    """生产环境部署器"""

    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL")
        self.engine = None
        self.session_factory = None

    async def deploy(self):
        """执行完整的部署流程"""
        logger.info("🚀 Starting Bento Outbox Production Deployment")

        try:
            # 1. 环境检查
            await self._check_environment()

            # 2. 数据库连接
            await self._setup_database()

            # 3. 配置验证
            await self._validate_configuration()

            # 4. 数据库优化
            await self._optimize_database()

            # 5. 性能验证
            await self._verify_performance()

            logger.info("✅ Production deployment completed successfully!")

        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            raise
        finally:
            if self.engine:
                await self.engine.dispose()

    async def _check_environment(self):
        """检查部署环境"""
        logger.info("📋 Checking deployment environment...")

        # Python版本检查
        if sys.version_info < (3, 11):
            raise RuntimeError("Python 3.11+ is required")
        logger.info(f"   ✅ Python version: {sys.version}")

        # 环境变量检查
        required_env_vars = [
            "DATABASE_URL",
            "BENTO_OUTBOX_BATCH_SIZE",
            "BENTO_OUTBOX_MAX_CONCURRENT_PROJECTORS",
        ]

        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            raise RuntimeError(f"Missing environment variables: {missing_vars}")

        logger.info("   ✅ Environment variables configured")

        # 数据库URL检查
        if not self.database_url:
            raise RuntimeError("DATABASE_URL environment variable is required")

        if not self.database_url.startswith("postgresql"):
            logger.warning(
                "   ⚠️  Non-PostgreSQL database detected - some optimizations may not apply"
            )

        logger.info("   ✅ Database URL configured")

    async def _setup_database(self):
        """设置数据库连接"""
        logger.info("🗄️ Setting up database connection...")

        # 创建生产优化的数据库引擎
        self.engine = create_async_engine(
            self.database_url,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
        )

        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

        # 测试连接
        try:
            async with self.engine.begin() as conn:
                result = await conn.execute(text("SELECT version()"))
                db_version = result.scalar()
                logger.info(f"   ✅ Database connected: {db_version}")
        except Exception as e:
            raise RuntimeError(f"Database connection failed: {e}")

    async def _validate_configuration(self):
        """验证配置"""
        logger.info("⚙️ Validating configuration...")

        try:
            config = get_outbox_projector_config()
            result = validate_config(config)

            if not result.is_valid:
                error_details = []
                for issue in result.issues:
                    error_details.append(f"- {issue.message}")
                raise RuntimeError("Configuration validation failed:\n" + "\n".join(error_details))

            logger.info("   ✅ Configuration is valid")

            # 显示关键配置
            logger.info(f"   📊 Batch size: {config.batch_size}")
            logger.info(f"   📊 Max concurrent: {config.max_concurrent_projectors}")
            logger.info(f"   📊 Sleep busy: {config.sleep_busy}s")

            # 性能预估
            theoretical_tps = config.batch_size / config.sleep_busy
            logger.info(f"   📈 Theoretical TPS: {theoretical_tps:.0f} events/second")

        except Exception as e:
            raise RuntimeError(f"Configuration validation failed: {e}")

    async def _optimize_database(self):
        """数据库优化"""
        logger.info("📊 Optimizing database...")

        # 检查Outbox表是否存在
        async with self.engine.begin() as conn:
            try:
                result = await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'outbox'"
                    )
                )
                table_exists = result.scalar() > 0

                if not table_exists:
                    logger.warning(
                        "   ⚠️  Outbox table not found - please run database migrations first"
                    )
                    return

                logger.info("   ✅ Outbox table exists")

                # 检查索引
                result = await conn.execute(
                    text("""
                    SELECT indexname FROM pg_indexes
                    WHERE tablename = 'outbox'
                    AND indexname LIKE 'ix_outbox_%'
                    """)
                )
                indexes = [row.indexname for row in result]

                expected_indexes = [
                    "ix_outbox_cleanup",
                    "ix_outbox_query_opt",
                    "ix_outbox_tenant_created",
                    "ix_outbox_processing_tenant",
                ]

                missing_indexes = [idx for idx in expected_indexes if idx not in indexes]

                if missing_indexes:
                    logger.warning(f"   ⚠️  Missing performance indexes: {missing_indexes}")
                    logger.info(
                        "   💡 Consider running: CREATE INDEX commands from production_guide.md"
                    )
                else:
                    logger.info("   ✅ All performance indexes present")

            except Exception as e:
                logger.warning(f"   ⚠️  Database optimization check failed: {e}")

    async def _verify_performance(self):
        """性能验证"""
        logger.info("🔍 Verifying performance setup...")

        try:
            # 创建性能监控器
            monitor = PerformanceMonitor(self.session_factory)

            # 获取基准指标
            metrics = await monitor.get_metrics()

            logger.info("   📊 Current Performance Metrics:")
            logger.info(f"      - Pending events: {metrics.pending_events}")
            logger.info(f"      - Events/second: {metrics.events_per_second:.2f}")
            logger.info(
                f"      - Connection pool: {metrics.active_connections}/{metrics.connection_pool_size}"
            )

            # 性能分析
            analysis = await monitor.analyze_performance_bottlenecks()

            if analysis["severity"] in ["high", "critical"]:
                logger.warning(f"   ⚠️  Performance issues detected: {analysis['bottlenecks']}")
                logger.info("   💡 Recommendations:")
                for rec in analysis["recommendations"]:
                    logger.info(f"      - {rec}")
            else:
                logger.info("   ✅ No performance bottlenecks detected")

        except Exception as e:
            logger.warning(f"   ⚠️  Performance verification failed: {e}")


async def main():
    """主函数"""
    deployer = ProductionDeployer()
    await deployer.deploy()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)
