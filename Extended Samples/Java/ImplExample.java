/*
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
*/

import com.ib.client.*;

public class ImplExample {

	public static void main(String[] args) throws InterruptedException {
		EWrapperImpl wrapper = new EWrapperImpl();
		
		final EClientSocket m_client = wrapper.getClient();
		final EReaderSignal m_signal = wrapper.getSignal();
		
		int port = 7496;
        
		m_client.eConnect("127.0.0.1", port, 2);
		final EReader reader = new EReader(m_client, m_signal);   
		
		reader.start();
		new Thread(() -> {
		    while (m_client.isConnected()) {
		        m_signal.waitForSignal();
		        try {
		            reader.processMsgs();
		        } catch (Exception e) {
		            System.out.println("Exception: "+e.getMessage());
		        }
		    }
		}).start();Thread.sleep(1000);

        int orderId = wrapper.getCurrentOrderId();
		orderPlacement(wrapper.getClient(), orderId);


		Thread.sleep(100000);
		m_client.eDisconnect();
	}
	
	private static void orderPlacement(EClientSocket client, int orderId) {
		
		Contract contract = new Contract();
		contract.symbol("AAPL");
		contract.secType("STK");
		contract.exchange("SMART");
		contract.currency("USD");

        Order order = new Order();
        order.action("BUY");
        order.orderType("MKT");
        order.totalQuantity(Decimal.get(5));


		client.placeOrder(orderId , contract, order);
	}
}