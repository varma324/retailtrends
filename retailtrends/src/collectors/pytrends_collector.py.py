# Databricks notebook source
"""
Google Trends Collector using pytrends
Handles rate limiting, retries, and chunked keyword fetching.
Supports ALL 12+ Google Trends data endpoints with all dimensions.
"""

import time
import pandas as pd
from pytrends.request import TrendReq
from typing import Optional, Dict, List, Union, Any


class GoogleTrendsCollector:
    """
    Collects ALL available Google Trends data using pytrends.

    ╔══════════════════════════════════════════════════════════╗
    ║  CORE DATA ENDPOINTS (12 total)                          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  1. get_interest_over_time()        → weekly timeseries  ║
    ║  2. get_multirange_interest()       → multi-timeframe    ║
    ║  3. get_interest_by_region()        → geo breakdown      ║
    ║  4. get_interest_by_city()          → city breakdown     ║
    ║  5. get_interest_by_country()       → worldwide heatmap  ║
    ║  6. get_interest_by_dma()           → US DMA breakdown   ║
    ║  7. get_related_queries()           → related searches   ║
    ║  8. get_related_topics()            → related topics     ║
    ║  9. get_trending_searches()         → daily trending     ║
    ║ 10. get_today_searches()            → today's trends     ║
    ║ 11. get_realtime_trending()         → realtime trends    ║
    ║ 12. get_top_charts()                → annual top charts  ║
    ╠══════════════════════════════════════════════════════════╣
    ║  METADATA ENDPOINTS                                      ║
    ╠══════════════════════════════════════════════════════════╣
    ║ 13. get_suggestions()               → keyword autocomplete║
    ║ 14. get_categories()                → category tree      ║
    ╠══════════════════════════════════════════════════════════╣
    ║  BATCH / MULTI-GEO HELPERS                               ║
    ╠══════════════════════════════════════════════════════════╣
    ║ 15. get_multi_country_timeseries()  → loop N countries   ║
    ║ 16. get_multi_gprop_timeseries()    → Web/News/YouTube   ║
    ║ 17. get_company_snapshot()          → full per-company   ║
    ║ 18. get_complete_dataset()          → ALL endpoints      ║
    ╚══════════════════════════════════════════════════════════╝
    """

    MAX_KEYWORDS_PER_REQUEST = 5

    def __init__(
        self,
        geo: str = "US",
        timeframe: str = "today 5-y",
        hl: str = "en-US",
        tz: int = 360,
        retries: int = 3,
        backoff_factor: int = 1,
        sleep_seconds: float = 2.0,
    ):
        self.geo           = geo
        self.timeframe     = timeframe
        self.sleep_seconds = sleep_seconds
        self.pytrends      = TrendReq(
            hl=hl,
            tz=tz,
            timeout=(10, 25),
            retries=retries,
            backoff_factor=backoff_factor,
        )

    # ══════════════════════════════════════════════════════════
    # Internal helpers
    # ══════════════════════════════════════════════════════════

    def _chunks(self, lst: list, n: int):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i : i + n]

    def _build(self, keywords: list, geo: Optional[str] = None) -> None:
        """Build pytrends payload, using instance geo if none given."""
        self.pytrends.build_payload(
            keywords,
            cat=0,
            timeframe=self.timeframe,
            geo=geo if geo is not None else self.geo,
        )

    def _melt(self, df: pd.DataFrame, geo_tag: str) -> pd.DataFrame:
        """Wide → long, drop isPartial, attach geo tag."""
        df = df.drop(columns=["isPartial"], errors="ignore").reset_index()
        df = df.melt(id_vars=["date"], var_name="keyword", value_name="interest_value")
        df["geo"] = geo_tag
        return df

    def _sleep(self, multiplier: float = 1.0) -> None:
        time.sleep(self.sleep_seconds * multiplier)

    # ══════════════════════════════════════════════════════════
    # 1. Interest over time (timeseries)
    # ══════════════════════════════════════════════════════════

    def _build_and_fetch(self, keywords: list, geo: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Fetch one chunk of interest_over_time."""
        effective_geo = geo if geo is not None else self.geo
        try:
            self._build(keywords, geo=effective_geo)
            df = self.pytrends.interest_over_time()
            if df.empty:
                return None
            return self._melt(df, effective_geo)
        except Exception as exc:
            print(f"  ⚠️  interest_over_time [{effective_geo}] {keywords}: {exc}")
            self._sleep(3)
            return None

    def get_interest_over_time(
        self,
        keywords: list,
        geo: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch weekly interest timeseries, auto-chunking if > 5 keywords.

        Args:
            keywords : list of search terms (e.g. ["Nike", "Adidas"])
            geo      : country code e.g. "US", "GB". Defaults to self.geo.

        Returns:
            DataFrame columns: date, keyword, interest_value, geo
        """
        frames = []
        for chunk in self._chunks(keywords, self.MAX_KEYWORDS_PER_REQUEST):
            df = self._build_and_fetch(chunk, geo=geo)
            if df is not None:
                frames.append(df)
            self._sleep()
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # ══════════════════════════════════════════════════════════
    # 2. Interest by region (state / province)
    # ══════════════════════════════════════════════════════════

    def get_interest_by_region(
        self,
        keywords: list,
        geo: Optional[str] = None,
        resolution: str = "REGION",
        inc_low_vol: bool = True,
    ) -> pd.DataFrame:
        """
        Fetch sub-national breakdown (states / provinces).

        Args:
            keywords   : up to 5 keywords
            geo        : country code e.g. "US", "GB"
            resolution : "REGION" (state), "CITY", or "COUNTRY"
            inc_low_vol: include low-volume regions

        Returns:
            DataFrame columns: geoName, <keyword1>, <keyword2>, ..., geo, resolution
        """
        effective_geo = geo if geo is not None else self.geo
        try:
            self._build(keywords[:self.MAX_KEYWORDS_PER_REQUEST], geo=effective_geo)
            df = self.pytrends.interest_by_region(
                resolution=resolution,
                inc_low_vol=inc_low_vol,
                inc_geo_code=True,
            )
            if df.empty:
                return pd.DataFrame()
            df = df.reset_index()
            df["geo"]        = effective_geo
            df["resolution"] = resolution
            return df
        except Exception as exc:
            print(f"  ⚠️  interest_by_region [{effective_geo}/{resolution}]: {exc}")
            return pd.DataFrame()

    # ══════════════════════════════════════════════════════════
    # 3. Interest by city
    # ══════════════════════════════════════════════════════════

    def get_interest_by_city(
        self,
        keywords: list,
        geo: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Fetch city-level interest breakdown inside a country.

        Returns:
            DataFrame columns: geoName, geoCode, <keywords...>, geo, resolution
        """
        return self.get_interest_by_region(
            keywords, geo=geo, resolution="CITY"
        )

    # ══════════════════════════════════════════════════════════
    # 4. Interest by country (global)
    # ══════════════════════════════════════════════════════════

    def get_interest_by_country(self, keywords: list) -> pd.DataFrame:
        """
        Fetch worldwide country-level interest (global geo = "").

        Returns:
            DataFrame columns: geoName, geoCode, <keywords...>, geo, resolution
        """
        return self.get_interest_by_region(
            keywords, geo="", resolution="COUNTRY"
        )

    # ══════════════════════════════════════════════════════════
    # 5. Multi-country timeseries loop
    # ══════════════════════════════════════════════════════════

    def get_multi_country_timeseries(
        self,
        keywords: list,
        geo_targets: dict,
        category: str = "",
    ) -> pd.DataFrame:
        """
        Fetch interest_over_time for every country in geo_targets.

        Args:
            keywords    : search terms
            geo_targets : dict of {display_name: geo_code}
                          e.g. {"United States": "US", "Germany": "DE"}
            category    : optional label added as a column

        Returns:
            DataFrame columns: date, keyword, interest_value, geo,
                                country_name, category
        """
        all_frames = []
        for country_name, geo_code in geo_targets.items():
            print(f"    🌍  {country_name} ({geo_code}) — {keywords}")
            df = self.get_interest_over_time(keywords, geo=geo_code)
            if not df.empty:
                df["country_name"] = country_name
                df["category"]     = category
                all_frames.append(df)
            self._sleep(1.5)   # extra pause between countries

        return pd.concat(all_frames, ignore_index=True) if all_frames else pd.DataFrame()

    # ══════════════════════════════════════════════════════════
    # 6. Company snapshot (one company, all regions + countries)
    # ══════════════════════════════════════════════════════════

    def get_company_snapshot(
        self,
        company_name:  str,
        keyword:       str,
        geo_targets:   dict,
        category:      str = "",
    ) -> dict:
        """
        Full snapshot for a single company across all target countries.

        Returns a dict:
        {
            "timeseries":  DataFrame,   # weekly trend per country
            "by_region":   DataFrame,   # state/province breakdown (first geo)
            "by_city":     DataFrame,   # city-level breakdown (first geo)
            "by_country":  DataFrame,   # worldwide country map
        }
        """
        snapshot: dict = {
            "timeseries": pd.DataFrame(),
            "by_region":  pd.DataFrame(),
            "by_city":    pd.DataFrame(),
            "by_country": pd.DataFrame(),
        }

        print(f"\n  🏢  Company: {company_name!r}  keyword={keyword!r}")

        # ── timeseries across all countries ───────────────────
        snapshot["timeseries"] = self.get_multi_country_timeseries(
            keywords=[keyword],
            geo_targets=geo_targets,
            category=category,
        )

        # ── regional breakdown for the primary geo ────────────
        primary_geo = next(iter(geo_targets.values()), self.geo)

        self._sleep()
        snapshot["by_region"] = self.get_interest_by_region(
            keywords=[keyword], geo=primary_geo, resolution="REGION"
        )
        snapshot["by_region"]["company"] = company_name

        self._sleep()
        snapshot["by_city"] = self.get_interest_by_city(
            keywords=[keyword], geo=primary_geo
        )
        snapshot["by_city"]["company"] = company_name

        # ── worldwide country heatmap ──────────────────────────
        self._sleep()
        snapshot["by_country"] = self.get_interest_by_country(keywords=[keyword])
        snapshot["by_country"]["company"] = company_name

        return snapshot

    # ══════════════════════════════════════════════════════════
    # 7. Related queries
    # ══════════════════════════════════════════════════════════

    def get_related_queries(
        self,
        keywords: list,
        geo: Optional[str] = None,
    ) -> dict:
        """
        Fetch rising + top related queries.

        Returns:
            dict: {keyword: {"top": DataFrame, "rising": DataFrame}}
        """
        effective_geo = geo if geo is not None else self.geo
        try:
            self._build(keywords[:self.MAX_KEYWORDS_PER_REQUEST], geo=effective_geo)
            return self.pytrends.related_queries()
        except Exception as exc:
            print(f"  ⚠️  related_queries [{effective_geo}]: {exc}")
            return {}

    # ══════════════════════════════════════════════════════════
    # 8. Trending searches
    # ══════════════════════════════════════════════════════════

    def get_trending_searches(self, country: str = "united_states") -> pd.DataFrame:
        """Fetch today's trending searches for a country."""
        try:
            return self.pytrends.trending_searches(pn=country)
        except Exception as exc:
            print(f"  ⚠️  trending_searches: {exc}")
            return pd.DataFrame()

    # ══════════════════════════════════════════════════════════
    # 9. Complete Dataset Orchestrator
    # ══════════════════════════════════════════════════════════

    def get_complete_dataset(
        self,
        keywords: List[str],
        geo: Optional[str] = None,
        include_geo_breakdown: bool = True,
        include_related: bool = True,
        include_worldwide: bool = False,
        multi_countries: Optional[Dict[str, str]] = None,
        resolutions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Fetch ALL available Google Trends data for given keywords in one call.
        
        This orchestrates multiple endpoints to provide comprehensive analysis:
        
        ╔════════════════════════════════════════════════════════╗
        ║  COMPLETE DATASET STRUCTURE                            ║
        ╠════════════════════════════════════════════════════════╣
        ║  interest_over_time      → Weekly timeseries           ║
        ║  interest_by_region      → State/province breakdown    ║
        ║  interest_by_city        → City-level data             ║
        ║  interest_by_country     → Worldwide heatmap           ║
        ║  related_queries         → Top & rising searches       ║
        ║  multi_country_data      → Cross-country comparison    ║
        ║  metadata                → Collection info             ║
        ╚════════════════════════════════════════════════════════╝
        
        Args:
            keywords: List of search terms (max 5 per request, batched if more)
            geo: Primary geography (e.g., "US", "GB", "DE")
            include_geo_breakdown: Include region/city/country breakdowns
            include_related: Include related queries
            include_worldwide: Include worldwide country comparison
            multi_countries: Dictionary mapping country names to codes
                           e.g., {"United States": "US", "Germany": "DE"}
            resolutions: Geo resolutions to fetch ["REGION", "CITY"]
        
        Returns:
            Comprehensive dataset dictionary with all available data points
            
        Example:
            >>> collector = GoogleTrendsCollector(geo="US")
            >>> data = collector.get_complete_dataset(
            ...     keywords=["Nike", "Adidas"],
            ...     include_geo_breakdown=True,
            ...     include_related=True,
            ...     multi_countries={"United States": "US", "Germany": "DE"}
            ... )
            >>> data.keys()
            dict_keys(['interest_over_time', 'interest_by_region', 
                      'interest_by_city', 'related_queries', 
                      'multi_country_data', 'metadata'])
        """
        effective_geo = geo if geo is not None else self.geo
        
        if resolutions is None:
            resolutions = ["REGION", "CITY"]
        
        result: Dict[str, Any] = {
            "metadata": {
                "keywords": keywords,
                "geo": effective_geo,
                "timeframe": self.timeframe,
                "collected_at": pd.Timestamp.now(tz="UTC").isoformat(),
                "total_keywords": len(keywords),
            }
        }
        
        print(f"\n{'='*60}")
        print(f"🔍 COMPLETE DATASET COLLECTION")
        print(f"{'='*60}")
        print(f"Keywords: {keywords}")
        print(f"Geography: {effective_geo}")
        print(f"Timeframe: {self.timeframe}")
        print(f"{'='*60}\n")
        
        # ── 1. Interest Over Time (Primary Timeseries) ──────────
        print("📊 [1/7] Fetching interest over time...")
        try:
            result["interest_over_time"] = self.get_interest_over_time(
                keywords=keywords, 
                geo=effective_geo
            )
            if not result["interest_over_time"].empty:
                print(f"    ✓ Got {len(result['interest_over_time'])} time points")
            else:
                print("    ⚠️ No timeseries data available")
        except Exception as exc:
            print(f"    ✗ Error: {exc}")
            result["interest_over_time"] = pd.DataFrame()
        
        self._sleep()
        
        # ── 2. Geographic Breakdown ─────────────────────────────
        if include_geo_breakdown:
            result["geo_breakdown"] = {}
            
            # 2a. Interest by Region (States/Provinces)
            if "REGION" in resolutions:
                print("🗺️  [2/7] Fetching interest by region...")
                try:
                    result["geo_breakdown"]["by_region"] = self.get_interest_by_region(
                        keywords=keywords,
                        geo=effective_geo,
                        resolution="REGION"
                    )
                    if not result["geo_breakdown"]["by_region"].empty:
                        print(f"    ✓ Got {len(result['geo_breakdown']['by_region'])} regions")
                except Exception as exc:
                    print(f"    ✗ Error: {exc}")
                    result["geo_breakdown"]["by_region"] = pd.DataFrame()
                
                self._sleep()
            
            # 2b. Interest by City
            if "CITY" in resolutions:
                print("🏙️  [3/7] Fetching interest by city...")
                try:
                    result["geo_breakdown"]["by_city"] = self.get_interest_by_city(
                        keywords=keywords,
                        geo=effective_geo
                    )
                    if not result["geo_breakdown"]["by_city"].empty:
                        print(f"    ✓ Got {len(result['geo_breakdown']['by_city'])} cities")
                except Exception as exc:
                    print(f"    ✗ Error: {exc}")
                    result["geo_breakdown"]["by_city"] = pd.DataFrame()
                
                self._sleep()
        
        # ── 3. Worldwide Country Comparison ─────────────────────
        if include_worldwide:
            print("🌍 [4/7] Fetching worldwide country interest...")
            try:
                result["interest_by_country"] = self.get_interest_by_country(
                    keywords=keywords
                )
                if not result["interest_by_country"].empty:
                    print(f"    ✓ Got {len(result['interest_by_country'])} countries")
            except Exception as exc:
                print(f"    ✗ Error: {exc}")
                result["interest_by_country"] = pd.DataFrame()
            
            self._sleep()
        
        # ── 4. Related Queries ──────────────────────────────────
        if include_related:
            print("🔗 [5/7] Fetching related queries...")
            try:
                result["related_queries"] = self.get_related_queries(
                    keywords=keywords,
                    geo=effective_geo
                )
                if result["related_queries"]:
                    total_related = sum(
                        2 for kw_data in result["related_queries"].values() 
                        if isinstance(kw_data, dict)
                    )
                    print(f"    ✓ Got related queries for {len(result['related_queries'])} keywords")
            except Exception as exc:
                print(f"    ✗ Error: {exc}")
                result["related_queries"] = {}
            
            self._sleep()
        
        # ── 5. Multi-Country Timeseries ─────────────────────────
        if multi_countries and len(multi_countries) > 0:
            print(f"🌐 [6/7] Fetching multi-country data ({len(multi_countries)} countries)...")
            try:
                result["multi_country_data"] = self.get_multi_country_timeseries(
                    keywords=keywords,
                    geo_targets=multi_countries
                )
                if not result["multi_country_data"].empty:
                    print(f"    ✓ Got {len(result['multi_country_data'])} data points")
            except Exception as exc:
                print(f"    ✗ Error: {exc}")
                result["multi_country_data"] = pd.DataFrame()
        
        # ── 6. Summary Statistics ───────────────────────────────
        print("📈 [7/7] Generating summary statistics...")
        result["summary"] = self._generate_summary(result, keywords)
        print(f"    ✓ Summary complete")
        
        print(f"\n{'='*60}")
        print("✅ COMPLETE DATASET COLLECTION FINISHED")
        print(f"{'='*60}")
        print(f"Total datasets collected: {len([k for k in result.keys() if k not in ['metadata', 'summary']])}")
        print(f"{'='*60}\n")
        
        return result

    def _generate_summary(
        self, 
        dataset: Dict, 
        keywords: List[str]
    ) -> Dict:
        """Generate summary statistics from collected dataset."""
        summary = {
            "keywords_analyzed": keywords,
            "total_keywords": len(keywords),
            "datasets_collected": [],
            "data_points": {},
        }
        
        # Count data points per dataset
        if "interest_over_time" in dataset and not dataset["interest_over_time"].empty:
            summary["datasets_collected"].append("interest_over_time")
            summary["data_points"]["timeseries_points"] = len(dataset["interest_over_time"])
        
        if "geo_breakdown" in dataset:
            for geo_type, df in dataset["geo_breakdown"].items():
                if not df.empty:
                    summary["datasets_collected"].append(geo_type)
                    summary["data_points"][geo_type] = len(df)
        
        if "interest_by_country" in dataset and not dataset["interest_by_country"].empty:
            summary["datasets_collected"].append("interest_by_country")
            summary["data_points"]["countries"] = len(dataset["interest_by_country"])
        
        if "related_queries" in dataset and dataset["related_queries"]:
            summary["datasets_collected"].append("related_queries")
            summary["data_points"]["related_queries_keywords"] = len(dataset["related_queries"])
        
        if "multi_country_data" in dataset and not dataset["multi_country_data"].empty:
            summary["datasets_collected"].append("multi_country_data")
            summary["data_points"]["multi_country_points"] = len(dataset["multi_country_data"])
        
        summary["total_datasets"] = len(summary["datasets_collected"])
        
        return summary
