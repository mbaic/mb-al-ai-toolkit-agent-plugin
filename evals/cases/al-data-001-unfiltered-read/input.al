codeunit 50101 "MB Item Turnover Report"
{
    procedure BuildTurnover(var TempBuffer: Record "Name/Value Buffer" temporary)
    var
        ItemLedgerEntry: Record "Item Ledger Entry";
        Item: Record Item;
        Total: Decimal;
    begin
        if Item.FindSet() then
            repeat
                ItemLedgerEntry.SetRange("Item No.", Item."No.");
                if ItemLedgerEntry.FindSet() then
                    repeat
                        Item.CalcFields(Inventory);
                        Total += ItemLedgerEntry."Cost Amount (Actual)";
                    until ItemLedgerEntry.Next() = 0;
                InsertBuffer(TempBuffer, Item."No.", Total);
                Total := 0;
            until Item.Next() = 0;
    end;

    local procedure InsertBuffer(var TempBuffer: Record "Name/Value Buffer" temporary; Name: Code[20]; Value: Decimal)
    begin
        TempBuffer.Init();
        TempBuffer.Name := Name;
        TempBuffer.Value := Format(Value);
        TempBuffer.Insert();
    end;
}
