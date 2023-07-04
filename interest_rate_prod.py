import numpy as np
import datetime as dt

class ZCB_curve:
    DAYS_IN_YEAR = 365
    
    def __init__(self,t:str,T_s,r_s,r_s_type='yield',compounding:float=1/2):
        """
        t is the date which is set to be time 0, in the form of str, for example, '2023-06-01'\n
        T_s is the list of maturities\n
        r_s is zero coupon yield, or zero coupon price, thus\n
        r_s_type should be 'yield' or 'discount factor'. If it is yield, r_s should be expressed in percent. r_s = 4.5 if the yield is 4.5%\n
        compounding is the compounding frequency, 0 if countinuously compounding\n
        """
        assert len(T_s) == len(r_s)
        assert r_s_type in ['yield','discount factor']
        self.t = dt.datetime.strptime(t,'%Y-%m-%d').date()
        self.T_s = np.array(T_s)
        self.r_s = np.array(r_s) 
        self.r_s_type = r_s_type
        self.compounding = compounding

        if self.r_s_type == 'yield':
            if self.compounding != 0:
                self.dcf = 1/(1+self.r_s*self.compounding/100)**(self.T_s/self.compounding)
            else:
                self.dcf = np.exp(-self.r_s*self.T_s/100)
        elif self.r_s_type == 'discount factor':
            self.r_s_type = 'yield'
            self.dcf = self.r_s
            if self.compounding != 0:
                self.r_s = ((1/self.dcf)**(self.compounding/self.T_s) - 1)/self.compounding
            else:
                self.r_s = np.log(1/self.dcf)/self.T_s
        else:
            print('invalid r_s_type')

    def get_curve(self,interpo = 'linear',which = 'yield'):
        """
        It returns a function. The function will take an input time and return a ZCB yield/discount factor
        The parameter which can be 'yield' or 'discount factor'
        """
        assert which in ['yield','discount factor']
        if interpo == 'linear':
            if which == 'yield':
                return lambda t: np.interp(t,self.T_s,self.r_s)
            else:
                return lambda t: np.interp(t,self.T_s,self.dcf)
        else:
            print('still working on it.')
    
    def get_discount_factor(self,t,T,interpo = 'linear'):
        """
        Calculate discount factor P(t,T). t and T can be date string with pattern '%Y-%m-%d' or a number in year.
        """
        # type manipulation for t and T
        if isinstance(t,str):
            tdt = dt.datetime.strptime(t,'%Y-%m-%d').date()
            assert self.t <= tdt
            t = (tdt - self.t).days/ZCB_curve.DAYS_IN_YEAR
        else:
            assert t >= 0

        if isinstance(T,str):
            Tdt = dt.datetime.strptime(T,'%Y-%m-%d').date()
            assert tdt <= Tdt
            T = (Tdt - self.t).days/ZCB_curve.DAYS_IN_YEAR
        else:
            assert t < T

        # construct the current yield curve
        curve = self.get_curve(interpo,which='discount factor')
        return curve(T)/curve(t)

    def get_forward_rate(self,t,T,interpo = 'linear',compounding=1/2):
        """
        Calculate forward rate (annualized) f(self.t:t,T). t and T can be date string with pattern '%Y-%m-%d' or a number in year.
        """
        # type manipulation for t and T
        if isinstance(t,str):
            tdt = dt.datetime.strptime(t,'%Y-%m-%d').date()
            assert self.t <= tdt
            t = (tdt - self.t).days/ZCB_curve.DAYS_IN_YEAR
        else:
            assert t >= 0

        if isinstance(T,str):
            Tdt = dt.datetime.strptime(T,'%Y-%m-%d').date()
            assert tdt <= Tdt
            T = (Tdt - self.t).days/ZCB_curve.DAYS_IN_YEAR
        else:
            assert t < T

        # construct the current yield curve
        curve = self.get_curve(interpo,which='yield')

        # calculate annualized forward rate based on different compounding frequency
        if compounding != 0:
            return ((((1+compounding*curve(T))**(T/compounding))/((1+compounding*curve(t))**(t/compounding)))**(compounding/(T-t)) - 1)/compounding
        else:
            return np.log(np.exp(curve(T)*T - curve(t)*t))/(T-t)
    
    def __str__(self):
        return f"{'-'*20}\nZero coupon yield curve on {self.t} \nby interpolating the spine points of {('time',self.r_s_type)}: {list(zip(self.T_s,self.r_s))}\nwith a compounding frequency of {self.compounding}.\n{'-'*20}"
    

class FRA:
    DAYS_IN_YEAR = 365
    
    def __init__(self,t:str,T,S,tau,N,ZCB_init:ZCB_curve,compounding=1/2,**kwarg):
        """
        t is the initiation date, in the form of 'YYYY-mm-dd', on which the FRA rate is determined.\n
        T is the maturity of the FRA contract in day.\n
        S is the settlement date in day.  t <= T < S.\n
        tau is the time difference between T and S in year.\n
        N is the notional amount.\n
        ZCB_unit is the ZCB curve.\n
        compounding is the compounding frequency, 1/2 by default 
        """
        self.t = t
        self.tau = tau
        self.N = N
        self.ZCB_init = ZCB_init
        self.compounding = compounding

        assert type(T) == type(S)
        self.dtt = dt.datetime.strptime(t,'%Y-%m-%d').date()   # convert the initiation date from string to datetime

        # define both the numerical version and datetime version of T and S
        if type(T) == str:      
            self.dtT = dt.datetime.strptime(T,'%Y-%m-%d').date()
            self.dtS = dt.datetime.strptime(S,'%Y-%m-%d').date()
            self.T = (self.dtT - self.dtt).days/FRA.DAYS_IN_YEAR
            self.S = (self.dtS - self.dtt).days/FRA.DAYS_IN_YEAR
            self.tau = (self.dtS - self.dtT).days/FRA.DAYS_IN_YEAR
        elif isinstance(T,(int,float)):
            self.dtT = self.dtt + dt.timedelta(days=T)
            self.dtS = self.dtt + dt.timedelta(days=S)
            self.T = T
            self.S = S
            assert self.tau == (self.S - self.T)/365
        else:
            print('check the type of T and S')
            raise TypeError
        
        # make sure T is before S
        assert self.dtT < self.dtS

        # calculate the price(annualized forward rate)
        assert self.dtt == ZCB_init.t     # make sure to align the time 0 of ZCB curve and the FRA contract
        ZCB_cur = ZCB_init.get_curve(which='discount factor')
        print(ZCB_cur(self.T/FRA.DAYS_IN_YEAR))
        print(ZCB_cur(self.S/FRA.DAYS_IN_YEAR))
        print(self.tau)
        self.K = (ZCB_cur(self.T/FRA.DAYS_IN_YEAR)/ZCB_cur(self.S/FRA.DAYS_IN_YEAR) - 1)/self.tau  # self.K is the price/strike/annualized forward rate. Note we assume simple interest here.

    def get_price(self):
        return self.K
    
    def set_price(self,K):
        self.K = K
    
    def get_value(self,t,ZCB:ZCB_curve):
        """
        For simplicity, we only calculate the value for the long position of the FRA.\n
        t is the current time in day when you want the value of the FRA. It can be either a number or a string following the pattern '%Y-%m-%d'.\n
        ZCB is the ZCB_curve object. The curve should start at time t aligning with the time you want to get the value
        """
        ZCB_cur_t = ZCB.get_curve(which='discount factor')      # get the yield curve at time t
        if isinstance(t,(float,int)):
            assert t <= self.T
            print(f'The date you want the FRA value is {self.dtt + dt.timedelta(days=FRA.DAYS_IN_YEAR*t)}.\nThe date when the ZCB curve starts is {ZCB.t}.')
            r_t_TS = (ZCB_cur_t((self.T-t)/FRA.DAYS_IN_YEAR)/ZCB_cur_t((self.S-t)/FRA.DAYS_IN_YEAR) - 1)/self.tau     # calculate the forward rate f(t:T,S)
            return self.N * self.tau * (r_t_TS - self.K)
        elif isinstance(t,str):
            print(f'The date you want the FRA value is {t}.\nThe date when the ZCB curve starts is {ZCB.t}.')
            dtt = dt.datetime.strptime(t,'%Y-%m-%d').date()
            t = (dtt - self.dtt).days/FRA.DAYS_IN_YEAR
            assert self.dtt <= dtt <= self.dtT
            r_t_TS = (ZCB_cur_t((self.T-t)/FRA.DAYS_IN_YEAR)/ZCB_cur_t((self.S-t)/FRA.DAYS_IN_YEAR) - 1)/self.tau 
            return self.N * self.tau * (r_t_TS - self.K)
        else:
            print('check the type of t')
            raise TypeError
            
    def __str__(self):
        return f"{'-'*20}\nFRA contract initiating on {self.dtt} with a maturity date {self.dtT}({self.T} days) and settlement date {self.dtS}({self.S} days).\nThe compounding frequency is {self.compounding}.\nThe notional amount is {self.N}.\n{'-'*20}"
        