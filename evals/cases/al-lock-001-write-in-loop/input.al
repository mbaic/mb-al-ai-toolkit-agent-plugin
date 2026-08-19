codeunit 50100 "MB Customer Credit Sync"
{
    procedure SyncCreditLimits(NewLimit: Decimal)
    var
        Customer: Record Customer;
        Setup: Record "Sales & Receivables Setup";
    begin
        Setup.Get();
        Customer.LockTable();
        Customer.FindSet(true);
        repeat
            Customer.Validate("Credit Limit (LCY)", NewLimit);
            Customer.Modify(true);
            Commit();
        until Customer.Next() = 0;
    end;

    procedure GetBlockedCustomerCount(): Integer
    var
        Customer: Record Customer;
    begin
        Customer.SetRange(Blocked, Customer.Blocked::All);
        Customer.SetLoadFields("No.");
        exit(Customer.Count());
    end;
}
