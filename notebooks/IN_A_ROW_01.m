% This is a minimalist in-a-row code for point in time (PIT) data 
clear
close all
% DATA = readtable('SPY_pit_1m_20250401_0842_w_deletions.csv');
% k_open= 568;
% k_close = 5251;
% DATA = readtable('SPY_pit_15s_20250422_0834_w_deletions.csv');
% k_open= 666;  
% k_close = 5350;
DATA = readtable('.\data\SPY_pit_5s_20250428_1148.csv');
k_open= 2;  
k_close = 90580;%15000;
N = 5;
S = DATA.close(k_open:k_close);
n= length(S);
% Initialization
V_0 = 10000;
U = V_0;
u(1) = 0;
V(1) = V_0;
V(2) = V(1);
IAR = 0;
for k = 2:n-1
    if S(k) > S(k-1)
       IAR = IAR + 1;
    else
       IAR = 0;
    end
    if IAR >= N;
        u(k) = sign(k-9360)*U;% REVERSION
    else
        u(k) = 0;
    end
    X(k) = (S(k+1)-S(k))/S(k);
    V(k+1) = V(k) + X(k)*u(k);
end
figure
 plot(S,'k','linewidth',3),  grid
 title('Trading  Prices Over the Period')
 figure
 plot(V,'k','linewidth',3), grid
 title('Account Value')
 xlabel('Trade Number')

% S(1) = DATA(1);
% for i = 1:n
%    X(i) = (S(i+1)-S(i))/S(i);
% end

% V(1:m+1) = V_0;
% u(1:m) = 0;
% for k = m+1:n   
%     % figure
%     % plot(S(1:m+1),'k','linewidth',3),  grid
%     % title('Training Sample Prices Over Window')
%     u(k) = 0;
%     p(k) = sum((1+sign(X(k-m:k-1)))/2)/m;
%     if p(k) >= 1
%      u(k) = -U;
%      TRADES = TRADES + 1;
%     end
%     % if p(k) <.01% .25%.3
%     %  u(k) = U;
%     % TRADES = TRADES + 1;
%     %end
%  V(k+1) = V(k) + u(k)*X(k);
% end
% NUMBER_OF_TRADES = TRADES
%  figure
%  plot(u,'k','linewidth',3), grid
%  title('Control (Bet Size)')
%  xlabel('Trade Number')
%  plot(p,'k','linewidth',3), grid
%  title('Probability of Uptick')
%  xlabel('Trade Number')
%  figure
%  plot(V,'k','linewidth',3), grid
%  title('Account Value')
%  xlabel('Trade Number')