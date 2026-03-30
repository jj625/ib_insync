/*
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
*/


import com.ib.client.*;

public class executionsTest extends DefaultEWrapper {

	private EReaderSignal readerSignal;
	private EClientSocket clientSocket;
	protected int currentOrderId = -1;
	
	public executionsTest() {
		readerSignal = new EJavaSignal();
		clientSocket = new EClientSocket(this, readerSignal);
	}
	
	public EClientSocket getClient() {
		return clientSocket;
	}
	
	public EReaderSignal getSignal() {
		return readerSignal;
	}
	
	public int getCurrentOrderId() {
		return currentOrderId+=1;
	}	

	public static void main(String[] args) throws InterruptedException {
		executionsTest wrapper = new executionsTest();
		
		final EClientSocket m_client = wrapper.getClient();
		final EReaderSignal m_signal = wrapper.getSignal();
		
		int port = 7496;

		m_client.eConnect("127.0.0.1", port, 1001);

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

		
		ExecutionFilter exFilter = new ExecutionFilter();
		m_client.reqExecutions(1234, exFilter);


		Thread.sleep(1000);
		m_client.eDisconnect();
	}

	@Override
	public void nextValidId(int orderId){
		currentOrderId = orderId;
	}
	
	@Override
	public void execDetails(int reqId, Contract contract, Execution execution) {
		System.out.println(EWrapperMsgGenerator.execDetails( reqId, contract, execution));
	}
	
	@Override
	public void execDetailsEnd(int reqId) {
		System.out.println("Exec Details End: " + EWrapperMsgGenerator.execDetailsEnd( reqId));
	}
	
	@Override
	public void error(int id, long errorTime, int errorCode, String errorMsg, String advancedOrderRejectJson) {
		String str = "Error. Id: " + id + ", Code: " + errorCode + ", Msg: " + errorMsg;
		if (advancedOrderRejectJson != null) {
			str += (", AdvancedOrderRejectJson: " + advancedOrderRejectJson);
		}
		System.out.println(str + "\n");
	}
    
}