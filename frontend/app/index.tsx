import React, { useState, useEffect, useCallback } from 'react';
import {
  Text,
  View,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  SafeAreaView,
  StatusBar,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';

// Types
interface CryptoCurrency {
  id: string;
  symbol: string;
  name: string;
  price_usd: number;
  market_cap_usd?: number;
  volume_24h_usd?: number;
  percent_change_1h?: number;
  percent_change_24h?: number;
  percent_change_7d?: number;
  percent_change_30d?: number;
  rank?: number;
  performance_score?: number;
  drawdown_score?: number;
  rebound_potential_score?: number;
  momentum_score?: number;
  total_score?: number;
  recovery_potential_75?: string;
  drawdown_percentage?: number;
  last_updated: string;
}

interface CryptoSummary {
  total_cryptos: number;
  periods: string[];
  last_update: string;
  top_performers: string[];
  market_sentiment: string;
}

const EXPO_PUBLIC_BACKEND_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || process.env.EXPO_PUBLIC_BACKEND_URL;

const PERIODS = [
  { key: '1h', label: '1 heure', emoji: '⚡' },
  { key: '24h', label: '24 heures', emoji: '📊' },
  { key: '7d', label: '1 semaine', emoji: '📈' },
  { key: '30d', label: '1 mois', emoji: '📅' },
];

const LIMITS = [
  { key: 50, label: '50 cryptos' },
  { key: 100, label: '100 cryptos' },
  { key: 200, label: '200 cryptos' },
];

export default function Index() {
  const [cryptos, setCryptos] = useState<CryptoCurrency[]>([]);
  const [summary, setSummary] = useState<CryptoSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState('24h');
  const [selectedLimit, setSelectedLimit] = useState(50);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  const fetchCryptoData = async (showLoading = true) => {
    try {
      if (showLoading) setLoading(true);

      console.log('Fetching crypto data from:', `${EXPO_PUBLIC_BACKEND_URL}/api/cryptos/ranking`);

      // Fetch rankings
      const rankingResponse = await fetch(
        `${EXPO_PUBLIC_BACKEND_URL}/api/cryptos/ranking?period=${selectedPeriod}&limit=${selectedLimit}&offset=0`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!rankingResponse.ok) {
        throw new Error(`HTTP error! status: ${rankingResponse.status}`);
      }

      const rankingData = await rankingResponse.json();
      setCryptos(rankingData);

      // Fetch summary
      const summaryResponse = await fetch(`${EXPO_PUBLIC_BACKEND_URL}/api/cryptos/summary`);
      if (summaryResponse.ok) {
        const summaryData = await summaryResponse.json();
        setSummary(summaryData);
      }

      setLastUpdate(new Date().toLocaleTimeString('fr-FR'));
    } catch (error) {
      console.error('Error fetching data:', error);
      Alert.alert(
        'Erreur',
        'Impossible de charger les données crypto. Vérifiez votre connexion internet.',
        [{ text: 'OK' }]
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchCryptoData(false);
  }, [selectedPeriod, selectedLimit]);

  useEffect(() => {
    fetchCryptoData();
  }, [selectedPeriod, selectedLimit]);

  const formatPrice = (price: number): string => {
    if (price >= 1000) {
      return `$${(price / 1000).toFixed(1)}K`;
    } else if (price >= 1) {
      return `$${price.toFixed(2)}`;
    } else {
      return `$${price.toFixed(6)}`;
    }
  };

  const formatMarketCap = (cap?: number): string => {
    if (!cap) return 'N/A';
    if (cap >= 1000000000) {
      return `$${(cap / 1000000000).toFixed(1)}B`;
    } else if (cap >= 1000000) {
      return `$${(cap / 1000000).toFixed(1)}M`;
    } else {
      return `$${(cap / 1000).toFixed(1)}K`;
    }
  };

  const formatPercentage = (pct?: number): string => {
    if (pct === undefined || pct === null) return 'N/A';
    const sign = pct >= 0 ? '+' : '';
    return `${sign}${pct.toFixed(2)}%`;
  };

  const getPercentageColor = (pct?: number): string => {
    if (pct === undefined || pct === null) return '#666666';
    return pct >= 0 ? '#00C851' : '#FF3547';
  };

  const getScoreColor = (score?: number): string => {
    if (!score) return '#666666';
    if (score >= 80) return '#00C851';
    if (score >= 60) return '#FFB347';
    if (score >= 40) return '#FF8C00';
    return '#FF3547';
  };

  const getRecoveryColor = (recovery?: string): string => {
    if (!recovery) return '#666666';
    const value = parseFloat(recovery.replace(/[+%]/g, ''));
    if (value >= 200) return '#8E44AD'; // Purple for Moonshot
    if (value >= 100) return '#E74C3C'; // Red for High
    if (value >= 50) return '#F39C12';  // Orange for Good
    return '#27AE60'; // Green for low recovery needed
  };

  const getRecoveryLabel = (recovery?: string): string => {
    if (!recovery) return '';
    const value = parseFloat(recovery.replace(/[+%]/g, ''));
    if (value >= 500) return 'Moonshot';
    if (value >= 200) return 'High';
    if (value >= 100) return 'Good';
    if (value >= 50) return 'Moderate';
    return 'Low';
  };

  const renderHeader = () => (
    <View style={styles.header}>
      <View style={styles.titleContainer}>
        <Text style={styles.title}>🚀 CryptoRebound Ranking</Text>
        <Text style={styles.subtitle}>
          Découvrez les meilleures opportunités de rebond crypto
        </Text>
      </View>

      {summary && (
        <View style={styles.summaryContainer}>
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryValue}>{summary.total_cryptos}</Text>
              <Text style={styles.summaryLabel}>Total cryptos</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryValue}>{summary.market_sentiment}</Text>
              <Text style={styles.summaryLabel}>Sentiment</Text>
            </View>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryValue}>{lastUpdate}</Text>
              <Text style={styles.summaryLabel}>Dernière MAJ</Text>
            </View>
          </View>
        </View>
      )}

      {/* Period Selector */}
      <View style={styles.selectorContainer}>
        <Text style={styles.selectorTitle}>Période:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.periodScroll}>
          {PERIODS.map((period) => (
            <TouchableOpacity
              key={period.key}
              style={[
                styles.periodButton,
                selectedPeriod === period.key && styles.periodButtonActive,
              ]}
              onPress={() => setSelectedPeriod(period.key)}
            >
              <Text style={styles.periodEmoji}>{period.emoji}</Text>
              <Text
                style={[
                  styles.periodText,
                  selectedPeriod === period.key && styles.periodTextActive,
                ]}
              >
                {period.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Limit Selector */}
      <View style={styles.selectorContainer}>
        <Text style={styles.selectorTitle}>Total cryptos:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.periodScroll}>
          {LIMITS.map((limit) => (
            <TouchableOpacity
              key={limit.key}
              style={[
                styles.limitButton,
                selectedLimit === limit.key && styles.limitButtonActive,
              ]}
              onPress={() => setSelectedLimit(limit.key)}
            >
              <Text
                style={[
                  styles.limitText,
                  selectedLimit === limit.key && styles.limitTextActive,
                ]}
              >
                {limit.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Legend */}
      <View style={styles.legendContainer}>
        <Text style={styles.legendTitle}>📋 Légende du Scoring Avancé</Text>
        
        <View style={styles.legendItem}>
          <View style={styles.legendHeader}>
            <Text style={styles.legendScore}>🎯 Score de Performance (15%)</Text>
          </View>
          <Text style={styles.legendDesc}>Performance actuelle sur la période sélectionnée</Text>
        </View>

        <View style={styles.legendItem}>
          <View style={styles.legendHeader}>
            <Text style={styles.legendScore}>📉 Score Drawdown (15%)</Text>
          </View>
          <Text style={styles.legendDesc}>Résistance aux chutes et gestion du risque</Text>
        </View>

        <View style={styles.legendItem}>
          <View style={styles.legendHeader}>
            <Text style={styles.legendScore}>🚀 Potentiel de Rebond (60%)</Text>
          </View>
          <Text style={styles.legendDesc}>Capacité de récupération basée sur la chute et la capitalisation</Text>
        </View>

        <View style={styles.legendItem}>
          <View style={styles.legendHeader}>
            <Text style={styles.legendScore}>⚡ Score Momentum (25%)</Text>
          </View>
          <Text style={styles.legendDesc}>Signes de reprise et dynamique récente</Text>
        </View>

        <View style={styles.recoveryLegend}>
          <Text style={styles.legendScore}>🎯 Potentiel Récupération 75%</Text>
          <Text style={styles.recoveryDesc}>
            <Text style={styles.optimizedText}>OPTIMISÉ:</Text> Gain nécessaire pour atteindre 75% du maximum annuel
          </Text>
          <Text style={styles.recoveryScale}>
            +500%+ = Moonshot | +100-200% = High | +50-100% = Good
          </Text>
        </View>
      </View>
    </View>
  );

  const renderCryptoItem = (crypto: CryptoCurrency, index: number) => (
    <View key={crypto.id} style={styles.cryptoCard}>
      <View style={styles.cryptoHeader}>
        <View style={styles.cryptoRank}>
          <Text style={styles.rankText}>{crypto.rank}</Text>
        </View>
        <View style={styles.cryptoInfo}>
          <Text style={styles.cryptoSymbol}>{crypto.symbol}</Text>
          <Text style={styles.cryptoName} numberOfLines={1}>{crypto.name}</Text>
        </View>
        <View style={styles.cryptoPrice}>
          <Text style={styles.priceText}>{formatPrice(crypto.price_usd)}</Text>
          <Text style={styles.marketCapText}>{formatMarketCap(crypto.market_cap_usd)}</Text>
        </View>
      </View>

      <View style={styles.cryptoScores}>
        <View style={styles.scoreRow}>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Total</Text>
            <Text style={[styles.scoreValue, { color: getScoreColor(crypto.total_score) }]}>
              {crypto.total_score?.toFixed(1) || 'N/A'}
            </Text>
          </View>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Performance</Text>
            <Text style={[styles.scoreValue, { color: getScoreColor(crypto.performance_score) }]}>
              {crypto.performance_score?.toFixed(1) || 'N/A'}
            </Text>
          </View>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Drawdown</Text>
            <Text style={[styles.scoreValue, { color: getScoreColor(crypto.drawdown_score) }]}>
              {crypto.drawdown_score?.toFixed(1) || 'N/A'}
            </Text>
          </View>
        </View>

        <View style={styles.scoreRow}>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Rebond</Text>
            <Text style={[styles.scoreValue, { color: getScoreColor(crypto.rebound_potential_score) }]}>
              {crypto.rebound_potential_score?.toFixed(1) || 'N/A'}
            </Text>
          </View>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Momentum</Text>
            <Text style={[styles.scoreValue, { color: getScoreColor(crypto.momentum_score) }]}>
              {crypto.momentum_score?.toFixed(1) || 'N/A'}
            </Text>
          </View>
          <View style={styles.scoreItem}>
            <Text style={styles.scoreLabel}>Récup 75%</Text>
            <View style={styles.recoveryContainer}>
              <Text style={[styles.recoveryValue, { color: getRecoveryColor(crypto.recovery_potential_75) }]}>
                {crypto.recovery_potential_75 || 'N/A'}
              </Text>
              <Text style={[styles.recoveryLabel, { color: getRecoveryColor(crypto.recovery_potential_75) }]}>
                {getRecoveryLabel(crypto.recovery_potential_75)}
              </Text>
            </View>
          </View>
        </View>
      </View>

      <View style={styles.cryptoChanges}>
        <View style={styles.changeItem}>
          <Text style={styles.changeLabel}>1h</Text>
          <Text style={[styles.changeValue, { color: getPercentageColor(crypto.percent_change_1h) }]}>
            {formatPercentage(crypto.percent_change_1h)}
          </Text>
        </View>
        <View style={styles.changeItem}>
          <Text style={styles.changeLabel}>24h</Text>
          <Text style={[styles.changeValue, { color: getPercentageColor(crypto.percent_change_24h) }]}>
            {formatPercentage(crypto.percent_change_24h)}
          </Text>
        </View>
        <View style={styles.changeItem}>
          <Text style={styles.changeLabel}>7d</Text>
          <Text style={[styles.changeValue, { color: getPercentageColor(crypto.percent_change_7d) }]}>
            {formatPercentage(crypto.percent_change_7d)}
          </Text>
        </View>
        <View style={styles.changeItem}>
          <Text style={styles.changeLabel}>30d</Text>
          <Text style={[styles.changeValue, { color: getPercentageColor(crypto.percent_change_30d) }]}>
            {formatPercentage(crypto.percent_change_30d)}
          </Text>
        </View>
      </View>
    </View>
  );

  if (loading && !refreshing) {
    return (
      <SafeAreaView style={styles.loadingContainer}>
        <StatusBar barStyle="light-content" backgroundColor="#0c0c0c" />
        <ActivityIndicator size="large" color="#FFB347" />
        <Text style={styles.loadingText}>Chargement des données crypto...</Text>
        <Text style={styles.loadingSubtext}>Analyse dynamique jusqu'à 5,000 cryptos</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0c0c0c" />
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#FFB347"
            colors={['#FFB347']}
          />
        }
        showsVerticalScrollIndicator={false}
      >
        {renderHeader()}

        <View style={styles.rankingHeader}>
          <Text style={styles.rankingTitle}>
            📊 Classement {PERIODS.find(p => p.key === selectedPeriod)?.label} ({cryptos.length} cryptos)
          </Text>
        </View>

        {cryptos.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>Aucune donnée disponible</Text>
            <Text style={styles.emptySubtext}>Tirez vers le bas pour actualiser</Text>
          </View>
        ) : (
          <View style={styles.cryptoList}>
            {cryptos.map((crypto, index) => renderCryptoItem(crypto, index))}
          </View>
        )}

        <View style={styles.footer}>
          <Text style={styles.footerText}>📊 Sources de Données Optimisées</Text>
          <View style={styles.sourceItem}>
            <Text style={styles.sourceStatus}>✅</Text>
            <View>
              <Text style={styles.sourceName}>CoinGecko API</Text>
              <Text style={styles.sourceDesc}>Données temps réel</Text>
            </View>
          </View>
          <View style={styles.sourceItem}>
            <Text style={styles.sourceStatus}>🧮</Text>
            <View>
              <Text style={styles.sourceName}>Calculé</Text>
              <Text style={styles.sourceDesc}>Algorithmes optimisés</Text>
            </View>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0c0c0c',
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: '#0c0c0c',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  scrollView: {
    flex: 1,
  },
  loadingText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
    marginTop: 20,
    textAlign: 'center',
  },
  loadingSubtext: {
    color: '#888888',
    fontSize: 14,
    marginTop: 10,
    textAlign: 'center',
  },
  header: {
    backgroundColor: '#1a1a1a',
    padding: 20,
    paddingTop: 10,
  },
  titleContainer: {
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#ffffff',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#cccccc',
    textAlign: 'center',
    lineHeight: 22,
  },
  summaryContainer: {
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
    flex: 1,
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#FFB347',
    marginBottom: 4,
  },
  summaryLabel: {
    fontSize: 12,
    color: '#888888',
    textAlign: 'center',
  },
  selectorContainer: {
    marginBottom: 16,
  },
  selectorTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 12,
  },
  periodScroll: {
    flexGrow: 0,
  },
  periodButton: {
    backgroundColor: '#2a2a2a',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    marginRight: 10,
    minWidth: 80,
    alignItems: 'center',
  },
  periodButtonActive: {
    backgroundColor: '#FFB347',
  },
  periodEmoji: {
    fontSize: 16,
    marginBottom: 2,
  },
  periodText: {
    fontSize: 12,
    color: '#cccccc',
    fontWeight: '500',
  },
  periodTextActive: {
    color: '#000000',
    fontWeight: '600',
  },
  limitButton: {
    backgroundColor: '#2a2a2a',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    marginRight: 10,
    alignItems: 'center',
  },
  limitButtonActive: {
    backgroundColor: '#FFB347',
  },
  limitText: {
    fontSize: 14,
    color: '#cccccc',
    fontWeight: '500',
  },
  limitTextActive: {
    color: '#000000',
    fontWeight: '600',
  },
  legendContainer: {
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    padding: 16,
    marginTop: 20,
  },
  legendTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 16,
    textAlign: 'center',
  },
  legendItem: {
    marginBottom: 12,
  },
  legendHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  legendScore: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFB347',
  },
  legendDesc: {
    fontSize: 14,
    color: '#cccccc',
    lineHeight: 20,
    paddingLeft: 4,
  },
  recoveryLegend: {
    marginTop: 8,
    padding: 12,
    backgroundColor: '#3a3a3a',
    borderRadius: 8,
  },
  recoveryDesc: {
    fontSize: 14,
    color: '#cccccc',
    marginVertical: 4,
  },
  optimizedText: {
    fontWeight: 'bold',
    color: '#FFB347',
  },
  recoveryScale: {
    fontSize: 13,
    color: '#888888',
    fontStyle: 'italic',
  },
  rankingHeader: {
    padding: 20,
    paddingBottom: 10,
  },
  rankingTitle: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#ffffff',
    textAlign: 'center',
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 18,
    color: '#ffffff',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#888888',
  },
  cryptoList: {
    paddingHorizontal: 20,
  },
  cryptoCard: {
    backgroundColor: '#1a1a1a',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#FFB347',
  },
  cryptoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  cryptoRank: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#FFB347',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  rankText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#000000',
  },
  cryptoInfo: {
    flex: 1,
  },
  cryptoSymbol: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 2,
  },
  cryptoName: {
    fontSize: 14,
    color: '#888888',
  },
  cryptoPrice: {
    alignItems: 'flex-end',
  },
  priceText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 2,
  },
  marketCapText: {
    fontSize: 12,
    color: '#888888',
  },
  cryptoScores: {
    marginBottom: 12,
  },
  scoreRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  scoreItem: {
    alignItems: 'center',
    flex: 1,
  },
  scoreLabel: {
    fontSize: 11,
    color: '#888888',
    marginBottom: 2,
    textAlign: 'center',
  },
  scoreValue: {
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  recoveryContainer: {
    alignItems: 'center',
  },
  recoveryValue: {
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  recoveryLabel: {
    fontSize: 9,
    fontWeight: '500',
    textAlign: 'center',
    marginTop: 1,
  },
  cryptoChanges: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#2a2a2a',
  },
  changeItem: {
    alignItems: 'center',
    flex: 1,
  },
  changeLabel: {
    fontSize: 11,
    color: '#888888',
    marginBottom: 2,
  },
  changeValue: {
    fontSize: 13,
    fontWeight: '600',
  },
  footer: {
    padding: 20,
    paddingTop: 30,
  },
  footerText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 16,
    textAlign: 'center',
  },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    paddingVertical: 8,
  },
  sourceStatus: {
    fontSize: 16,
    marginRight: 12,
  },
  sourceName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFB347',
    marginBottom: 2,
  },
  sourceDesc: {
    fontSize: 14,
    color: '#cccccc',
  },
});