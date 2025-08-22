#!/usr/bin/env python3
"""
以太坊Gas费用查询脚本
支持多种数据源获取当前gas价格
"""

import requests
import json
from typing import Dict, Optional
import time

class EthGasTracker:
    def __init__(self):
        """初始化Gas追踪器"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_gas_from_etherscan(self, api_key: Optional[str] = None) -> Dict:
        """
        从Etherscan获取gas数据

        Args:
            api_key: Etherscan API密钥（可选，有密钥会更稳定）

        Returns:
            包含gas费用信息的字典
        """
        try:
            url = "https://api.etherscan.io/api"
            params = {
                "module": "gastracker",
                "action": "gasoracle"
            }

            if api_key:
                params["apikey"] = api_key

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if data["status"] == "1":
                result = data["result"]
                # 处理可能的小数值，向上取整
                import math
                return {
                    "source": "Etherscan",
                    "safe_gas": math.ceil(float(result["SafeGasPrice"])),
                    "standard_gas": math.ceil(float(result["ProposeGasPrice"])),
                    "fast_gas": math.ceil(float(result["FastGasPrice"])),
                    "unit": "Gwei",
                    "timestamp": time.time()
                }
            else:
                raise Exception(f"Etherscan API错误: {data.get('message', '未知错误')}")

        except Exception as e:
            print(f"从Etherscan获取数据失败: {e}")
            return {}

    def _get_gas_from_backup_api(self) -> Dict:
        """备用API获取gas数据"""
        try:
            url = "https://api.blocknative.com/gasprices/blockprices"
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; Gas-Tracker/1.0)'}
            response = self.session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            if "blockPrices" in data and data["blockPrices"]:
                latest = data["blockPrices"][0]
                gas_prices = latest["estimatedPrices"]

                # 找到不同优先级的价格
                slow = next((p for p in gas_prices if p["confidence"] <= 70), gas_prices[0])
                standard = next((p for p in gas_prices if 70 < p["confidence"] <= 90), gas_prices[-1])
                fast = next((p for p in gas_prices if p["confidence"] > 90), gas_prices[-1])

                return {
                    "source": "BlockNative",
                    "safe_gas": int(slow["price"]),
                    "standard_gas": int(standard["price"]),
                    "fast_gas": int(fast["price"]),
                    "unit": "Gwei",
                    "timestamp": time.time()
                }
            else:
                raise Exception("无有效数据")

        except Exception as e:
            print(f"从备用API获取数据失败: {e}")
            return {}

    def get_gas_from_web3_rpc(self, rpc_urls: list = None) -> Dict:
        """
        通过Web3 RPC直接获取gas价格（使用多个免费RPC）

        Args:
            rpc_urls: RPC节点URL列表

        Returns:
            包含gas费用信息的字典
        """
        if rpc_urls is None:
            rpc_urls = [
                "https://ethereum.publicnode.com",
                "https://cloudflare-eth.com",
                "https://rpc.builder0x69.io"
            ]

        for rpc_url in rpc_urls:
            try:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "eth_gasPrice",
                    "params": [],
                    "id": 1
                }

                response = self.session.post(rpc_url, json=payload, timeout=8)
                response.raise_for_status()

                data = response.json()
                if "result" in data:
                    # 将wei转换为gwei
                    gas_price_wei = int(data["result"], 16)
                    gas_price_gwei = gas_price_wei / 10**9

                    return {
                        "source": f"Web3 RPC ({rpc_url.split('//')[1].split('.')[0]})",
                        "current_gas": round(gas_price_gwei, 2),
                        "unit": "Gwei",
                        "timestamp": time.time()
                    }
                else:
                    continue  # 尝试下一个RPC

            except Exception as e:
                print(f"RPC {rpc_url} 失败: {e}")
                continue

        return {}

    def get_all_gas_data(self, etherscan_api_key: Optional[str] = None) -> Dict:
        """
        从所有数据源获取gas数据

        Args:
            etherscan_api_key: Etherscan API密钥（可选）

        Returns:
            汇总的gas费用信息
        """
        results = {}

        print("正在获取以太坊Gas费用数据...")

        # 从Etherscan获取
        etherscan_data = self.get_gas_from_etherscan(etherscan_api_key)
        if etherscan_data:
            results["etherscan"] = etherscan_data

        # 从RPC获取
        rpc_data = self.get_gas_from_web3_rpc()
        if rpc_data:
            results["rpc"] = rpc_data

        return results

    def print_gas_info(self, gas_data: Dict):
        """
        格式化打印gas信息

        Args:
            gas_data: gas数据字典
        """
        if not gas_data:
            print("❌ 未能获取到任何gas数据")
            return

        print("\n" + "="*50)
        print("🔥 以太坊Gas费用实时数据")
        print("="*50)

        for source, data in gas_data.items():
            print(f"\n📊 数据源: {data['source']}")
            print("-" * 30)

            if 'safe_gas' in data:
                print(f"🐌 慢速交易:   {data['safe_gas']} {data['unit']}")
                print(f"⚡ 标准交易:   {data['standard_gas']} {data['unit']}")
                print(f"🚀 快速交易:   {data['fast_gas']} {data['unit']}")
                if 'fastest_gas' in data:
                    print(f"💨 极速交易:   {data['fastest_gas']} {data['unit']}")
                if 'instant_gas' in data:
                    print(f"💨 瞬时交易:   {data['instant_gas']} {data['unit']}")
            elif 'current_gas' in data:
                print(f"📈 当前价格:   {data['current_gas']} {data['unit']}")

            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data['timestamp']))
            print(f"🕒 更新时间:   {timestamp}")

        print("\n" + "="*50)

def main():
    """主函数"""
    tracker = EthGasTracker()

    # 可选：设置Etherscan API密钥（从 https://etherscan.io/apis 获取）
    # etherscan_api_key = "YOUR_API_KEY_HERE"
    etherscan_api_key = None

    try:
        # 获取所有gas数据
        gas_data = tracker.get_all_gas_data(etherscan_api_key)

        # 打印结果
        tracker.print_gas_info(gas_data)

        # 保存到JSON文件（可选）
        if gas_data:
            with open('eth_gas_data.json', 'w', encoding='utf-8') as f:
                json.dump(gas_data, f, ensure_ascii=False, indent=2)
            print(f"💾 数据已保存到 eth_gas_data.json")

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")

if __name__ == "__main__":
    main()