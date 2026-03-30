% This version aims to generalize to different times delta_t between trades
clear
close all
DATA = readtable('SPY_pit_1m_20250401_0842_w_deletions.csv');
%DATA = readtable('SPY_pit_15s_20250422_0834_w_deletions.csv');
k_open= 568%666 (for April 22; % shift by 1 dues to line 1 included in count 
k_close = 5251%5251 (for April 22);
delta_t = 10%300;%seconds between trades 
m = 10% number of training samples of returns
n = floor((k_close-k_open)*5/delta_t); % number of 5 min intervals
DATA = DATA.average(k_open:k_close);
scale = 10^4;
% Initialization 
V(1) = 10000;
S(1) = DATA(1);
for i =1:n+1  
    S(i) = DATA(1+ (i-1)*delta_t/5);
end
%S(m+1) = 556.966 %demo purposes only
for i = 1:n
   X(i) = (S(i+1)-S(i))/S(i);
end
%demonstrate interior max possibility
figure
 plot(S,'k','linewidth',3),  grid
 title('Training Sample Prices Over the Day')
ii = 0;
for k = 1:n-m-1    
 %  figure
 %  plot(S(k:k+m),'k','linewidth',3),  grid
 % title('Training Sample Prices Over Window')
  for KK = -1:.01:1
      ii = ii+1;
      K(ii) = KK;
      ELG(ii) = scale*(1/m)*sum(log(1+KK*X(k:k+m)));
  end
 %  figure
 % plot(K,ELG,'r','linewidth',3), grid
 % title('Empirical Logarithmic Growth Over Window')
 % xlabel('Feedback Gain K')
 [a b] = max(ELG);
 K_star(k) = K(b);
 ELG_star(k) = a;
 V(k+1) = (1+K_star(k)*X(m+k+1))*V(k);
end
 figure
 plot(K_star,'k','linewidth',3), grid
 title('Optimal Feedbck Vesrsus Trade Number')
 xlabel('Feedback Gain K')
figure
plot(V,'k','linewidth',3), grid
 title('Account Value')
 xlabel('Trade Number')