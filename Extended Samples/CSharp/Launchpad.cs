/*
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
*/

using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace C__Tutorial_Library
{
    internal class Launchpad
    {
        public static void Main()
        {
            CurrentTimeTest.TimeMain();

            ContractDetailsTest.ContractMain();

            LiveData.LiveDataMain();

            historicalDataTest.historicalMain();

            historicalUpdateTest.historicalUpdateMain();

            PlaceOrderTest.PlaceOrderMain();

            ComboOrderTest.ComboOrderMain();

            BracketOrderTest.BracketOrderMain();

            AccountPortfolioTest.AccountMain();

            ExecutionsTest.ExecutionsMain();

            ScannerParamsTest.ScannerParamsTestMain();

            ScannerTest.ScannerMain();

            TickByTickTest.TickByTickTestMain();

            PositionsTest.PositionMain();

            SixLegComboOrder.SixLegMain();

        }
    }
}
