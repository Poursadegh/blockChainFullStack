import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWebSocket } from '@/hooks/useWebSocket';
import { PriceChart } from '@/components/charts/PriceChart';
import { OrderBookChart } from '@/components/charts/OrderBookChart';
import { VolumeChart } from '@/components/charts/VolumeChart';

interface OrderBookEntry {
  price: number;
  amount: number;
  total: number;
}

interface MarketData {
  symbol: string;
  lastPrice: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: number;
}

// Sample data for charts
const samplePriceData = Array.from({ length: 24 }, (_, i) => ({
  timestamp: Date.now() - (23 - i) * 3600000,
  price: 45000 + Math.random() * 1000,
}));

const sampleOrderBookData = [
  ...Array.from({ length: 10 }, (_, i) => ({
    price: 45000 - (i * 100),
    amount: Math.random() * 2,
    type: 'bid' as const,
  })),
  ...Array.from({ length: 10 }, (_, i) => ({
    price: 45000 + ((i + 1) * 100),
    amount: Math.random() * 2,
    type: 'ask' as const,
  })),
];

const sampleVolumeData = Array.from({ length: 24 }, (_, i) => ({
  timestamp: Date.now() - (23 - i) * 3600000,
  volume: Math.random() * 100,
  type: Math.random() > 0.5 ? 'buy' as const : 'sell' as const,
}));

export default function TradingPage() {
  const { user } = useAuth();
  const [selectedPair, setSelectedPair] = useState('BTC/USDT');
  const [orderType, setOrderType] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState('');
  const [orderBook, setOrderBook] = useState<{
    bids: OrderBookEntry[];
    asks: OrderBookEntry[];
  }>({ bids: [], asks: [] });
  const [marketData, setMarketData] = useState<MarketData | null>(null);

  const { sendMessage, lastMessage } = useWebSocket('wss://api.example.com/ws');

  useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'orderbook') {
        setOrderBook(data.data);
      } else if (data.type === 'market') {
        setMarketData(data.data);
      }
    }
  }, [lastMessage]);

  const handleOrderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await sendMessage(JSON.stringify({
        type: 'place_order',
        data: {
          pair: selectedPair,
          type: orderType,
          amount: parseFloat(amount),
          price: parseFloat(price),
        },
      }));
      setAmount('');
      setPrice('');
    } catch (error) {
      console.error('Failed to place order:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Market Data */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Market Overview</CardTitle>
          </CardHeader>
          <CardContent>
            {marketData && (
              <div className="grid grid-cols-5 gap-4">
                <div>
                  <Label>Last Price</Label>
                  <div className="text-2xl font-bold">${marketData.lastPrice}</div>
                </div>
                <div>
                  <Label>24h Change</Label>
                  <div className={`text-2xl font-bold ${marketData.change24h >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {marketData.change24h}%
                  </div>
                </div>
                <div>
                  <Label>24h High</Label>
                  <div className="text-xl">${marketData.high24h}</div>
                </div>
                <div>
                  <Label>24h Low</Label>
                  <div className="text-xl">${marketData.low24h}</div>
                </div>
                <div>
                  <Label>24h Volume</Label>
                  <div className="text-xl">${marketData.volume24h}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Price Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Price Chart</CardTitle>
          </CardHeader>
          <CardContent>
            <PriceChart data={samplePriceData} height={400} />
          </CardContent>
        </Card>

        {/* Order Book */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Order Book</CardTitle>
          </CardHeader>
          <CardContent>
            <OrderBookChart data={sampleOrderBookData} height={400} />
          </CardContent>
        </Card>

        {/* Volume Chart */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Volume</CardTitle>
          </CardHeader>
          <CardContent>
            <VolumeChart data={sampleVolumeData} height={200} />
          </CardContent>
        </Card>

        {/* Trading Interface */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Place Order</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="buy" onValueChange={(value) => setOrderType(value as 'buy' | 'sell')}>
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="buy">Buy</TabsTrigger>
                <TabsTrigger value="sell">Sell</TabsTrigger>
              </TabsList>
              <TabsContent value="buy">
                <form onSubmit={handleOrderSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Amount</Label>
                    <Input
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="Enter amount"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Price</Label>
                    <Input
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="Enter price"
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full bg-green-500 hover:bg-green-600">
                    Buy {selectedPair}
                  </Button>
                </form>
              </TabsContent>
              <TabsContent value="sell">
                <form onSubmit={handleOrderSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Amount</Label>
                    <Input
                      type="number"
                      value={amount}
                      onChange={(e) => setAmount(e.target.value)}
                      placeholder="Enter amount"
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Price</Label>
                    <Input
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      placeholder="Enter price"
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full bg-red-500 hover:bg-red-600">
                    Sell {selectedPair}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 