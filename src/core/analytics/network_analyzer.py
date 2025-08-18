#!/usr/bin/env python3
"""
Network Analyzer - IP address, subnet, and geographic cluster analysis
Analyzes network patterns and geographic distribution of threats
"""

import ipaddress
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

from .base_analyzer import BaseAnalyzer


class NetworkAnalyzer(BaseAnalyzer):
    """Analyzes network-related threat patterns"""
    
    def get_network_analysis(self) -> Dict[str, Any]:
        """Comprehensive network analysis including subnets and geo clusters"""
        return self._safe_execute(
            "Network Analysis",
            self._perform_network_analysis
        )
        
    def _perform_network_analysis(self) -> Dict[str, Any]:
        """Internal network analysis logic"""
        # Get IP address data
        ip_data = self._get_ip_data()
        
        # Subnet analysis
        subnet_analysis = self._analyze_subnets(ip_data)
        
        # Geographic clusters
        geo_clusters = self._analyze_geographic_clusters(ip_data)
        
        # ASN patterns
        asn_analysis = self._analyze_asn_patterns(ip_data)
        
        return {
            "subnet_analysis": subnet_analysis,
            "geographic_clusters": geo_clusters,
            "asn_analysis": asn_analysis,
            "network_summary": {
                "total_ips": len(ip_data),
                "unique_subnets": len(subnet_analysis.get("high_risk_subnets", [])),
                "high_risk_countries": len(
                    [c for c in geo_clusters if c.get("risk_level") == "HIGH"]
                ),
            },
        }
        
    def _get_ip_data(self) -> List[Tuple]:
        """Get IP address data with country and threat level"""
        query = "SELECT ip_address, country, threat_level FROM blacklist_entries"
        return self._execute_query(query)
        
    def _analyze_subnets(self, ip_data: List[Tuple]) -> Dict[str, Any]:
        """Analyze subnet patterns for high-risk networks"""
        subnet_counter = Counter()
        
        for ip, country, threat_level in ip_data:
            try:
                network = ipaddress.ip_network(f"{ip}/24", strict=False)
                subnet_counter[str(network)] += 1
            except:
                continue
                
        high_risk_subnets = [
            {"subnet": subnet, "threat_count": count}
            for subnet, count in subnet_counter.most_common(20)
            if count > 5
        ]
        
        return {
            "high_risk_subnets": high_risk_subnets,
            "total_subnets": len(subnet_counter),
            "avg_threats_per_subnet": (
                sum(subnet_counter.values()) / len(subnet_counter)
                if subnet_counter
                else 0
            ),
        }
        
    def _analyze_geographic_clusters(self, ip_data: List[Tuple]) -> List[Dict[str, Any]]:
        """Analyze geographic clustering of threats"""
        country_stats = defaultdict(lambda: {"count": 0, "threat_levels": Counter()})
        
        for ip, country, threat_level in ip_data:
            if country and country != "UNKNOWN":
                country_stats[country]["count"] += 1
                country_stats[country]["threat_levels"][threat_level] += 1
                
        clusters = []
        for country, stats in country_stats.items():
            critical_ratio = stats["threat_levels"].get("CRITICAL", 0) / stats["count"]
            high_ratio = stats["threat_levels"].get("HIGH", 0) / stats["count"]
            
            risk_level = "LOW"
            if critical_ratio > 0.3 or high_ratio > 0.5:
                risk_level = "HIGH"
            elif critical_ratio > 0.1 or high_ratio > 0.3:
                risk_level = "MEDIUM"
                
            clusters.append({
                "country": country,
                "threat_count": stats["count"],
                "risk_level": risk_level,
                "threat_distribution": dict(stats["threat_levels"]),
            })
            
        return sorted(clusters, key=lambda x: x["threat_count"], reverse=True)
        
    def _analyze_asn_patterns(self, ip_data: List[Tuple]) -> Dict[str, Any]:
        """Analyze ASN patterns (basic IP range analysis)"""
        # Since we don't have actual ASN data, analyze public vs private IPs
        private_ranges = 0
        public_ranges = 0
        
        for ip, _, _ in ip_data:
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private:
                    private_ranges += 1
                else:
                    public_ranges += 1
            except:
                continue
                
        total_ips = private_ranges + public_ranges
        return {
            "private_ip_count": private_ranges,
            "public_ip_count": public_ranges,
            "private_ratio": (
                private_ranges / total_ips if total_ips > 0 else 0
            ),
        }


if __name__ == "__main__":
    # Validation function
    analyzer = NetworkAnalyzer()
    print("🌐 Testing Network Analyzer...")
    
    result = analyzer.get_network_analysis()
    if result:
        net_summary = result.get("network_summary", {})
        print(f"  - Total IPs: {net_summary.get('total_ips', 0)}")
        print(f"  - Unique subnets: {net_summary.get('unique_subnets', 0)}")
        print("✅ Network Analyzer validation successful")
    else:
        print("❌ Network Analyzer validation failed")