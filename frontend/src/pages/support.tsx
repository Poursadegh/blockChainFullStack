import { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { useWebSocket } from '@/hooks/useWebSocket';

interface SupportTicket {
  id: number;
  title: string;
  description: string;
  status: string;
  created_at: string;
  messages: TicketMessage[];
}

interface TicketMessage {
  id: number;
  message: string;
  is_staff: boolean;
  created_at: string;
}

interface FAQItem {
  id: number;
  question: string;
  answer: string;
  category: string;
}

export default function SupportPage() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [faqItems, setFaqItems] = useState<FAQItem[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [newMessage, setNewMessage] = useState('');
  const [newTicket, setNewTicket] = useState({
    title: '',
    description: '',
    category: 'general',
  });

  const { sendMessage, lastMessage } = useWebSocket('wss://api.example.com/support');

  useEffect(() => {
    // Fetch tickets
    const fetchTickets = async () => {
      try {
        const response = await fetch('/api/support/tickets');
        const data = await response.json();
        setTickets(data);
      } catch (error) {
        console.error('Failed to fetch tickets:', error);
      }
    };

    // Fetch FAQ items
    const fetchFAQ = async () => {
      try {
        const response = await fetch('/api/support/faq');
        const data = await response.json();
        setFaqItems(data);
      } catch (error) {
        console.error('Failed to fetch FAQ items:', error);
      }
    };

    fetchTickets();
    fetchFAQ();
  }, []);

  useEffect(() => {
    if (lastMessage) {
      const data = JSON.parse(lastMessage.data);
      if (data.type === 'ticket_message') {
        setTickets((prevTickets) =>
          prevTickets.map((ticket) =>
            ticket.id === data.ticket_id
              ? { ...ticket, messages: [...ticket.messages, data.message] }
              : ticket
          )
        );
      }
    }
  }, [lastMessage]);

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/support/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTicket),
      });
      const data = await response.json();
      setTickets([...tickets, data]);
      setNewTicket({ title: '', description: '', category: 'general' });
    } catch (error) {
      console.error('Failed to create ticket:', error);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !newMessage.trim()) return;

    try {
      await sendMessage(
        JSON.stringify({
          type: 'send_message',
          ticket_id: selectedTicket.id,
          message: newMessage,
        })
      );
      setNewMessage('');
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  return (
    <div className="container mx-auto p-4">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Tickets List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Support Tickets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {tickets.map((ticket) => (
                <div
                  key={ticket.id}
                  className={`p-4 border rounded cursor-pointer ${
                    selectedTicket?.id === ticket.id ? 'bg-muted' : ''
                  }`}
                  onClick={() => setSelectedTicket(ticket)}
                >
                  <div className="font-bold">{ticket.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {new Date(ticket.created_at).toLocaleString()}
                  </div>
                  <div className="text-sm">{ticket.status}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Ticket Details */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>
              {selectedTicket ? selectedTicket.title : 'Create New Ticket'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedTicket ? (
              <div className="space-y-4">
                <div className="space-y-2">
                  {selectedTicket.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`p-4 rounded ${
                        message.is_staff ? 'bg-muted' : 'bg-primary/10'
                      }`}
                    >
                      <div className="text-sm text-muted-foreground">
                        {message.is_staff ? 'Support' : 'You'} -{' '}
                        {new Date(message.created_at).toLocaleString()}
                      </div>
                      <div>{message.message}</div>
                    </div>
                  ))}
                </div>
                <form onSubmit={handleSendMessage} className="space-y-4">
                  <Textarea
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Type your message..."
                    required
                  />
                  <Button type="submit">Send Message</Button>
                </form>
              </div>
            ) : (
              <form onSubmit={handleCreateTicket} className="space-y-4">
                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    value={newTicket.title}
                    onChange={(e) =>
                      setNewTicket({ ...newTicket, title: e.target.value })
                    }
                    placeholder="Enter ticket title"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <select
                    className="w-full p-2 border rounded"
                    value={newTicket.category}
                    onChange={(e) =>
                      setNewTicket({ ...newTicket, category: e.target.value })
                    }
                  >
                    <option value="general">General</option>
                    <option value="technical">Technical</option>
                    <option value="account">Account</option>
                    <option value="trading">Trading</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={newTicket.description}
                    onChange={(e) =>
                      setNewTicket({ ...newTicket, description: e.target.value })
                    }
                    placeholder="Describe your issue"
                    required
                  />
                </div>
                <Button type="submit">Create Ticket</Button>
              </form>
            )}
          </CardContent>
        </Card>

        {/* FAQ */}
        <Card className="lg:col-span-3">
          <CardHeader>
            <CardTitle>Frequently Asked Questions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {faqItems.map((item) => (
                <div key={item.id} className="border rounded p-4">
                  <div className="font-bold">{item.question}</div>
                  <div className="text-muted-foreground">{item.answer}</div>
                  <div className="text-sm text-muted-foreground">
                    Category: {item.category}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 