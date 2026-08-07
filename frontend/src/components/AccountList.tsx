import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAccounts } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { AccountStatement } from "@/components/AccountStatement";

/** Badge colour per account type — purely visual, no business logic. */
const TYPE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  ASSET: "default",
  LIABILITY: "secondary",
  EQUITY: "outline",
  REVENUE: "secondary",
  EXPENSE: "outline",
};

/**
 * AccountList — shows all accounts. Clicking a row expands the statement
 * view inline (US-2, US-3).
 */
export function AccountList() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data: accounts, isLoading, error } = useQuery({
    queryKey: ["accounts"],
    queryFn: getAccounts,
  });

  if (isLoading) return <p className="text-muted-foreground p-4">Loading accounts…</p>;
  if (error) return <p className="text-destructive p-4">Failed to load accounts.</p>;

  const selectedAccount = accounts?.find((a) => a.id === selectedId);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Account ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Normal Balance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {accounts?.map((account) => (
                <TableRow
                  key={account.id}
                  className="cursor-pointer"
                  onClick={() =>
                    setSelectedId(selectedId === account.id ? null : account.id)
                  }
                  aria-selected={selectedId === account.id}
                >
                  <TableCell className="font-mono text-sm">{account.code}</TableCell>
                  <TableCell>{account.name}</TableCell>
                  <TableCell>
                    <Badge variant={TYPE_VARIANT[account.type] ?? "outline"}>
                      {account.type}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {account.normal_balance}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Inline statement — shown when an account row is selected */}
      {selectedId && selectedAccount && (
        <AccountStatement
          accountId={selectedId}
          accountName={selectedAccount.name}
        />
      )}
    </div>
  );
}
