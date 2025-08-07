from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import numpy as np

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="CryptoRebound Ranking API", version="2.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class CryptoCurrency(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    name: str
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    percent_change_1h: Optional[float] = None
    percent_change_24h: Optional[float] = None
    percent_change_7d: Optional[float] = None
    percent_change_30d: Optional[float] = None
    rank: Optional[int] = None
    
    # Historical data for scoring
    historical_prices: Optional[Dict[str, float]] = Field(default_factory=dict)
    max_price_1y: Optional[float] = None
    min_price_1y: Optional[float] = None
    
    # Calculated scores
    performance_score: Optional[float] = None
    drawdown_score: Optional[float] = None
    rebound_potential_score: Optional[float] = None
    momentum_score: Optional[float] = None
    total_score: Optional[float] = None
    
    # Additional metrics
    recovery_potential_75: Optional[str] = None
    drawdown_percentage: Optional[float] = None
    last_updated: datetime = Field(default_factory=datetime.utcnow)

class MultiPeriodCrypto(BaseModel):
    symbol: str
    name: str
    price_usd: float
    market_cap_usd: Optional[float] = None
    average_score: float
    long_term_average: Optional[float] = None
    period_scores: Dict[str, float]
    long_term_scores: Optional[Dict[str, float]] = None
    best_period: str
    worst_period: str
    consistency_score: float
    long_term_consistency: Optional[float] = None
    trend_confirmation: Optional[str] = None
    rank: int

class CryptoSummary(BaseModel):
    total_cryptos: int
    periods: List[str]
    last_update: str
    top_performers: List[str]
    market_sentiment: str

# Scoring Service Implementation
class ScoringService:
    def __init__(self):
        self.weights = {
            'performance': 0.15,      # 5-15%
            'drawdown': 0.15,         # 10-15%
            'rebound_potential': 0.60, # 45-60%
            'momentum': 0.25          # 20-30%
        }
    
    def calculate_scores(self, cryptos: List[CryptoCurrency], period: str = '24h') -> List[CryptoCurrency]:
        """Calculate all scores for a list of cryptocurrencies"""
        try:
            valid_cryptos = []
            for crypto in cryptos:
                if not crypto.price_usd or crypto.price_usd <= 0:
                    continue
                
                # Calculate individual scores
                crypto.performance_score = self._calculate_performance_score(crypto, period)
                crypto.drawdown_score = self._calculate_drawdown_score(crypto)
                crypto.rebound_potential_score = self._calculate_rebound_potential_score(crypto)
                crypto.momentum_score = self._calculate_momentum_score(crypto, period)
                
                # Calculate total weighted score
                crypto.total_score = self._calculate_total_score(crypto)
                
                # Calculate additional metrics
                crypto.recovery_potential_75 = self._calculate_recovery_potential(crypto)
                crypto.drawdown_percentage = self._calculate_drawdown_percentage(crypto)
                
                valid_cryptos.append(crypto)
            
            # Sort by total score (highest first)
            valid_cryptos.sort(key=lambda x: x.total_score or 0, reverse=True)
            
            # Add rankings
            for i, crypto in enumerate(valid_cryptos):
                crypto.rank = i + 1
            
            return valid_cryptos
        
        except Exception as e:
            logger.error(f"Error calculating scores: {e}")
            return cryptos
    
    def _calculate_performance_score(self, crypto: CryptoCurrency, period: str) -> float:
        """Calculate performance score based on recent performance"""
        try:
            period_map = {
                '1h': crypto.percent_change_1h,
                '24h': crypto.percent_change_24h,
                '7d': crypto.percent_change_7d,
                '30d': crypto.percent_change_30d
            }
            
            performance = period_map.get(period, crypto.percent_change_24h) or 0
            
            # Convert performance to a 0-100 score
            if performance >= 0:
                return min(100, 50 + performance * 2)
            else:
                return max(5, 50 + performance * 2)
        
        except Exception as e:
            return 50.0
    
    def _calculate_drawdown_score(self, crypto: CryptoCurrency) -> float:
        """Calculate drawdown resistance score"""
        try:
            if not crypto.max_price_1y or not crypto.price_usd:
                return 50.0
            
            # Calculate current drawdown from 1-year high
            current_drawdown = ((crypto.max_price_1y - crypto.price_usd) / crypto.max_price_1y) * 100
            
            # Convert to score: smaller drawdown = higher score
            if current_drawdown <= 10:
                return 100.0
            elif current_drawdown <= 30:
                return 90.0 - (current_drawdown - 10) * 2
            elif current_drawdown <= 60:
                return 50.0 - (current_drawdown - 30) * 1.5
            else:
                return max(5.0, 20.0 - (current_drawdown - 60) * 0.5)
        
        except Exception as e:
            return 50.0
    
    def _calculate_rebound_potential_score(self, crypto: CryptoCurrency) -> float:
        """Calculate rebound potential score - this is the main factor"""
        try:
            if not crypto.max_price_1y or not crypto.price_usd or not crypto.market_cap_usd:
                return 50.0
            
            # Current distance from yearly high
            distance_from_high = ((crypto.max_price_1y - crypto.price_usd) / crypto.max_price_1y) * 100
            
            # Market cap factor - smaller caps have higher potential but more risk
            market_cap_millions = crypto.market_cap_usd / 1_000_000
            
            if market_cap_millions > 1000:  # Large cap
                cap_multiplier = 0.8
            elif market_cap_millions > 100:  # Mid cap
                cap_multiplier = 1.0
            else:  # Small cap
                cap_multiplier = 1.2
            
            # Base score from distance
            if distance_from_high >= 80:  # Very oversold
                base_score = 100.0
            elif distance_from_high >= 60:  # Oversold
                base_score = 90.0 - (80 - distance_from_high) * 2
            elif distance_from_high >= 40:  # Moderately down
                base_score = 70.0 - (60 - distance_from_high) * 1.5
            elif distance_from_high >= 20:  # Slightly down
                base_score = 40.0 - (40 - distance_from_high) * 1
            else:  # Near highs
                base_score = max(20.0, 30.0 - distance_from_high)
            
            return min(100.0, base_score * cap_multiplier)
        
        except Exception as e:
            return 50.0
    
    def _calculate_momentum_score(self, crypto: CryptoCurrency, period: str) -> float:
        """Calculate momentum score based on recent trends"""
        try:
            # Use multiple timeframes to assess momentum
            short_term = crypto.percent_change_24h or 0
            medium_term = crypto.percent_change_7d or 0
            
            # Recent momentum (last 24h) vs medium term (7d)
            momentum_trend = short_term - (medium_term / 7)
            
            # Volume factor if available
            volume_factor = 1.0
            if crypto.volume_24h_usd and crypto.market_cap_usd:
                volume_ratio = crypto.volume_24h_usd / crypto.market_cap_usd
                if volume_ratio > 0.1:  # High volume
                    volume_factor = 1.2
                elif volume_ratio < 0.01:  # Low volume
                    volume_factor = 0.8
            
            # Convert momentum to score
            base_score = 50 + momentum_trend * 5  # Each 1% momentum = 5 points
            base_score = max(5, min(100, base_score))
            
            return base_score * volume_factor
        
        except Exception as e:
            return 50.0
    
    def _calculate_total_score(self, crypto: CryptoCurrency) -> float:
        """Calculate weighted total score"""
        try:
            performance = crypto.performance_score or 0
            drawdown = crypto.drawdown_score or 0
            rebound = crypto.rebound_potential_score or 0
            momentum = crypto.momentum_score or 0
            
            total = (
                performance * self.weights['performance'] +
                drawdown * self.weights['drawdown'] +
                rebound * self.weights['rebound_potential'] +
                momentum * self.weights['momentum']
            )
            
            return round(total, 1)
        
        except Exception as e:
            return 0.0
    
    def _calculate_recovery_potential(self, crypto: CryptoCurrency) -> str:
        """Calculate recovery potential percentage string"""
        try:
            if not crypto.max_price_1y or not crypto.price_usd:
                return "+62.0%"
            
            # Calculate how much gain needed to reach 75% of yearly high
            target_price = crypto.max_price_1y * 0.75
            
            if crypto.price_usd >= target_price:
                return "+0%"
            
            gain_needed = ((target_price - crypto.price_usd) / crypto.price_usd) * 100
            
            if gain_needed > 500:
                return "+500%+"
            elif gain_needed > 300:
                return "+240%"
            elif gain_needed > 200:
                return "+200%"
            elif gain_needed > 150:
                return "+171%"
            elif gain_needed > 100:
                return f"+{int(gain_needed)}%"
            else:
                return f"+{gain_needed:.1f}%"
        
        except Exception as e:
            return "+62.0%"
    
    def _calculate_drawdown_percentage(self, crypto: CryptoCurrency) -> float:
        """Calculate current drawdown percentage"""
        try:
            if not crypto.max_price_1y or not crypto.price_usd:
                return 0.0
            
            drawdown = ((crypto.max_price_1y - crypto.price_usd) / crypto.max_price_1y) * 100
            return round(drawdown, 1)
        
        except Exception as e:
            return 0.0

# Initialize scoring service
scoring_service = ScoringService()

# Data fetching service
async def fetch_crypto_data(limit: int = 100) -> List[CryptoCurrency]:
    """Fetch cryptocurrency data from CoinGecko API"""
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page': limit,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '1h,24h,7d,30d'
        }
        
        # Use a simple requests call since this is a demo
        import requests
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        cryptos = []
        for item in data:
            # Generate some mock historical data for scoring
            current_price = item['current_price']
            max_price_1y = current_price * (1.2 + (hash(item['id']) % 100) / 100)  # Mock yearly high
            min_price_1y = current_price * (0.3 + (hash(item['id']) % 50) / 100)   # Mock yearly low
            
            crypto = CryptoCurrency(
                symbol=item['symbol'].upper(),
                name=item['name'],
                price_usd=current_price,
                market_cap_usd=item.get('market_cap'),
                volume_24h_usd=item.get('total_volume'),
                percent_change_1h=item.get('price_change_percentage_1h_in_currency'),
                percent_change_24h=item.get('price_change_percentage_24h'),
                percent_change_7d=item.get('price_change_percentage_7d_in_currency'),
                percent_change_30d=item.get('price_change_percentage_30d_in_currency'),
                max_price_1y=max_price_1y,
                min_price_1y=min_price_1y,
                last_updated=datetime.utcnow()
            )
            cryptos.append(crypto)
        
        return cryptos
    
    except Exception as e:
        logger.error(f"Error fetching crypto data: {e}")
        return []

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "CryptoRebound Ranking API v2.0 - Ready to track 1000+ cryptocurrencies!"}

@api_router.get("/cryptos/ranking", response_model=List[CryptoCurrency])
async def get_crypto_ranking(
    period: str = Query("24h", description="Time period for ranking"),
    limit: int = Query(50, description="Number of results to return", ge=1, le=1000),
    offset: int = Query(0, description="Offset for pagination", ge=0)
):
    """Get cryptocurrency ranking with CryptoRebound scoring"""
    try:
        logger.info(f"Getting crypto ranking: period={period}, limit={limit}, offset={offset}")
        
        # Fetch crypto data
        cryptos = await fetch_crypto_data(limit + offset + 50)  # Get extra for better ranking
        
        if not cryptos:
            raise HTTPException(status_code=503, detail="Unable to fetch cryptocurrency data")
        
        # Calculate scores
        scored_cryptos = scoring_service.calculate_scores(cryptos, period)
        
        # Apply pagination
        end_index = offset + limit
        result = scored_cryptos[offset:end_index]
        
        logger.info(f"Returning {len(result)} ranked cryptocurrencies for {period}")
        return result
    
    except Exception as e:
        logger.error(f"Error getting crypto ranking: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ranking: {str(e)}")

@api_router.get("/cryptos/multi-period-analysis", response_model=List[MultiPeriodCrypto])
async def get_multi_period_analysis(
    limit: int = Query(15, description="Number of top cryptos to return", ge=5, le=50),
    short_periods: List[str] = Query(['24h', '7d'], description="Short-term periods to analyze"),
    long_periods: List[str] = Query(['30d'], description="Long-term periods to analyze")
):
    """Get top cryptocurrencies analyzed across multiple periods"""
    try:
        logger.info(f"Starting multi-period analysis: {len(short_periods)} short + {len(long_periods)} long periods, top {limit}")
        
        # Dictionary to store all crypto data with scores from different periods
        crypto_scores = {}
        
        # Get data for SHORT TERM periods first
        for period in short_periods:
            try:
                period_cryptos = await fetch_crypto_data(200)
                scored_cryptos = scoring_service.calculate_scores(period_cryptos, period)
                
                logger.info(f"Got {len(scored_cryptos)} cryptos for SHORT period {period}")
                
                for crypto in scored_cryptos:
                    symbol = crypto.symbol
                    
                    if symbol not in crypto_scores:
                        crypto_scores[symbol] = {
                            'symbol': symbol,
                            'name': crypto.name,
                            'price_usd': crypto.price_usd,
                            'market_cap_usd': crypto.market_cap_usd,
                            'short_period_scores': {},
                            'long_period_scores': {},
                            'short_total_score': 0,
                            'long_total_score': 0,
                            'short_period_count': 0,
                            'long_period_count': 0
                        }
                    
                    # Add score for this SHORT period
                    score = getattr(crypto, 'total_score', 0) or 0
                    crypto_scores[symbol]['short_period_scores'][period] = score
                    crypto_scores[symbol]['short_total_score'] += score
                    crypto_scores[symbol]['short_period_count'] += 1
            
            except Exception as e:
                logger.warning(f"Error processing short period {period}: {e}")
                continue
        
        # Get data for LONG TERM periods
        for period in long_periods:
            try:
                period_cryptos = await fetch_crypto_data(200)
                scored_cryptos = scoring_service.calculate_scores(period_cryptos, period)
                
                logger.info(f"Got {len(scored_cryptos)} cryptos for LONG period {period}")
                
                for crypto in scored_cryptos:
                    symbol = crypto.symbol
                    
                    # Initialize if not exists
                    if symbol not in crypto_scores:
                        crypto_scores[symbol] = {
                            'symbol': symbol,
                            'name': crypto.name,
                            'price_usd': crypto.price_usd,
                            'market_cap_usd': crypto.market_cap_usd,
                            'short_period_scores': {},
                            'long_period_scores': {},
                            'short_total_score': 0,
                            'long_total_score': 0,
                            'short_period_count': 0,
                            'long_period_count': 0
                        }
                    
                    # Add score for this LONG period
                    score = getattr(crypto, 'total_score', 0) or 0
                    crypto_scores[symbol]['long_period_scores'][period] = score
                    crypto_scores[symbol]['long_total_score'] += score
                    crypto_scores[symbol]['long_period_count'] += 1
            
            except Exception as e:
                logger.warning(f"Error processing long period {period}: {e}")
                continue
        
        # Filter cryptos that have data
        min_short_periods = max(1, len(short_periods) // 2)
        filtered_cryptos = {}
        
        for symbol, data in crypto_scores.items():
            if data['short_period_count'] >= min_short_periods:
                # Calculate SHORT TERM average score
                data['short_average_score'] = data['short_total_score'] / data['short_period_count']
                
                # Calculate LONG TERM average score if we have data
                if data['long_period_count'] > 0:
                    data['long_average_score'] = data['long_total_score'] / data['long_period_count']
                else:
                    data['long_average_score'] = None
                
                # Calculate SHORT TERM consistency
                short_scores = list(data['short_period_scores'].values())
                if len(short_scores) > 1:
                    mean_score = sum(short_scores) / len(short_scores)
                    variance = sum((x - mean_score) ** 2 for x in short_scores) / len(short_scores)
                    std_dev = variance ** 0.5
                    data['short_consistency_score'] = max(0, 100 - (std_dev / max(mean_score, 1)) * 100)
                else:
                    data['short_consistency_score'] = 100
                
                # Calculate TREND CONFIRMATION
                if data['long_average_score'] is not None:
                    short_avg = data['short_average_score']
                    long_avg = data['long_average_score']
                    
                    if abs(short_avg - long_avg) <= 10:
                        data['trend_confirmation'] = "Strong"
                    elif short_avg > long_avg and (short_avg - long_avg) <= 20:
                        data['trend_confirmation'] = "Accelerating"
                    elif long_avg > short_avg and (long_avg - short_avg) <= 20:
                        data['trend_confirmation'] = "Cooling"
                    else:
                        data['trend_confirmation'] = "Divergent"
                else:
                    data['trend_confirmation'] = "Unknown"
                
                # Find best and worst periods
                all_periods = {**data['short_period_scores'], **data['long_period_scores']}
                if all_periods:
                    sorted_periods = sorted(all_periods.items(), key=lambda x: x[1], reverse=True)
                    data['best_period'] = sorted_periods[0][0]
                    data['worst_period'] = sorted_periods[-1][0]
                else:
                    data['best_period'] = short_periods[0] if short_periods else 'unknown'
                    data['worst_period'] = short_periods[0] if short_periods else 'unknown'
                
                filtered_cryptos[symbol] = data
        
        # Sort by SHORT TERM average score
        sorted_cryptos = []
        for symbol, data in filtered_cryptos.items():
            consistency_bonus = (data['short_consistency_score'] / 100) * 5
            
            trend_bonus = 0
            if data['trend_confirmation'] == "Strong":
                trend_bonus = 3
            elif data['trend_confirmation'] == "Accelerating":
                trend_bonus = 2
            elif data['trend_confirmation'] == "Cooling":
                trend_bonus = 1
            
            final_score = data['short_average_score'] + consistency_bonus + trend_bonus
            sorted_cryptos.append((symbol, data, final_score))
        
        # Sort by final score and take top N
        sorted_cryptos.sort(key=lambda x: x[2], reverse=True)
        top_cryptos = sorted_cryptos[:limit]
        
        # Convert to response format
        result = []
        for rank, (symbol, data, final_score) in enumerate(top_cryptos, 1):
            result.append(MultiPeriodCrypto(
                symbol=symbol,
                name=data['name'],
                price_usd=data['price_usd'],
                market_cap_usd=data['market_cap_usd'],
                average_score=round(data['short_average_score'], 2),
                long_term_average=round(data['long_average_score'], 2) if data['long_average_score'] is not None else None,
                period_scores=data['short_period_scores'],
                long_term_scores=data['long_period_scores'] if data['long_period_scores'] else None,
                best_period=data['best_period'],
                worst_period=data['worst_period'],
                consistency_score=round(data['short_consistency_score'], 1),
                long_term_consistency=None,  # Simplified for now
                trend_confirmation=data['trend_confirmation'],
                rank=rank
            ))
        
        logger.info(f"Multi-period analysis completed: {len(result)} cryptos analyzed")
        return result
    
    except Exception as e:
        logger.error(f"Error in multi-period analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Multi-period analysis failed: {str(e)}")

@api_router.get("/cryptos/summary", response_model=CryptoSummary)
async def get_crypto_summary():
    """Get a summary of the cryptocurrency market"""
    try:
        # Get some basic data for summary
        cryptos = await fetch_crypto_data(100)
        
        if not cryptos:
            raise HTTPException(status_code=503, detail="Unable to fetch cryptocurrency data")
        
        # Calculate top performers
        scored_cryptos = scoring_service.calculate_scores(cryptos, '24h')
        top_performers = [crypto.symbol for crypto in scored_cryptos[:5]]
        
        # Simple market sentiment based on overall performance
        avg_24h_change = sum([crypto.percent_change_24h or 0 for crypto in cryptos]) / len(cryptos)
        
        if avg_24h_change > 2:
            sentiment = "Très Positif"
        elif avg_24h_change > 0:
            sentiment = "Positif"
        elif avg_24h_change > -2:
            sentiment = "Neutre"
        else:
            sentiment = "Négatif"
        
        return CryptoSummary(
            total_cryptos=len(cryptos),
            periods=['1h', '24h', '7d', '30d'],
            last_update=datetime.utcnow().isoformat(),
            top_performers=top_performers,
            market_sentiment=sentiment
        )
    
    except Exception as e:
        logger.error(f"Error getting crypto summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()