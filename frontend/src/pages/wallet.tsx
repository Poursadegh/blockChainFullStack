import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface WalletBalance {
  currency: string;
  balance: number;
  available: number;
  inOrders: number;
}

interface Transaction {
  id: number;
  type: 'deposit' | 'withdrawal' | 'trade';
  currency: string;
  amount: number;
  status: string;
  timestamp: string;
}

export default function WalletPage() {
  const { user } = useAuth();
  const [balances, setBalances] = useState<WalletBalance[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedCurrency, setSelectedCurrency] = useState('BTC');
  const [amount, setAmount] = useState('');
  const [address, setAddress] = useState('');

  useEffect(() => {
    // Fetch wallet balances
    const fetchBalances = async () => {
      try {
        const response = await fetch('/api/wallet/balances');
        const data = await response.json();
        setBalances(data);
      } catch (error) {
        console.error('Failed to fetch balances:', error);
      }
    };

    // Fetch transactions
    const fetchTransactions = async () => {
      try {
        const response = await fetch('/api/wallet/transactions');
        const data = await response.json();
        setTransactions(data);
      } catch (error) {
        console.error('Failed to fetch transactions:', error);
      }
    };

    fetchBalances();
    fetchTransactions();
  }, []);

  const handleDeposit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/wallet/deposit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ currency: selectedCurrency }),
      });
      const data = await response.json();
      setAddress(data.address);
    } catch (error) {
      console.error('Failed to generate deposit address:', error);
    }
  };

  const handleWithdrawal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await fetch('/api/wallet/withdraw', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          currency: selectedCurrency,
          amount: parseFloat(amount),
          address: address,
        }),
      });
      setAmount('');
      setAddress('');
    } catch (error) {
      console.error('Failed to process withdrawal:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Wallet Balances */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Wallet Balances</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {balances.map((balance) => (
                <Card key={balance.currency}>
                  <CardContent className="p-4">
                    <div className="text-lg font-bold">{balance.currency}</div>
                    <div className="text-2xl font-bold">${balance.balance.toFixed(8)}</div>
                    <div className="text-sm text-muted-foreground">
                      Available: ${balance.available.toFixed(8)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      In Orders: ${balance.inOrders.toFixed(8)}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Deposit/Withdrawal */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Deposit/Withdraw</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="deposit">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="deposit">Deposit</TabsTrigger>
                <TabsTrigger value="withdraw">Withdraw</TabsTrigger>
              </TabsList>
              <TabsContent value="deposit">
                <form onSubmit={handleDeposit} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Currency</Label>
                    <select
                      className="w-full p-2 border rounded"
                      value={selectedCurrency}
                      onChange={(e) => setSelectedCurrency(e.target.value)}
                    >
                      {balances.map((balance) => (
                        <option key={balance.currency} value={balance.currency}>
                          {balance.currency}
                        </option>
                      ))}
                    </select>
                  </div>
                  {address && (
                    <div className="space-y-2">
                      <Label>Deposit Address</Label>
                      <div className="p-2 bg-muted rounded break-all">{address}</div>
                    </div>
                  )}
                  <Button type="submit" className="w-full">
                    Generate Deposit Address
                  </Button>
                </form>
              </TabsContent>
              <TabsContent value="withdraw">
                <form onSubmit={handleWithdrawal} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Currency</Label>
                    <select
                      className="w-full p-2 border rounded"
                      value={selectedCurrency}
                      onChange={(e) => setSelectedCurrency(e.target.value)}
                    >
                      {balances.map((balance) => (
                        <option key={balance.currency} value={balance.currency}>
                          {balance.currency}
                        </option>
                      ))}
                    </select>
                  </div>
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
                    <Label>Address</Label>
                    <Input
                      value={address}
                      onChange={(e) => setAddress(e.target.value)}
                      placeholder="Enter destination address"
                      required
                    />
                  </div>
                  <Button type="submit" className="w-full">
                    Withdraw
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Transaction History */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Transaction History</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Currency</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((transaction) => (
                  <TableRow key={transaction.id}>
                    <TableCell>{transaction.type}</TableCell>
                    <TableCell>{transaction.currency}</TableCell>
                    <TableCell>{transaction.amount}</TableCell>
                    <TableCell>{transaction.status}</TableCell>
                    <TableCell>{new Date(transaction.timestamp).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 