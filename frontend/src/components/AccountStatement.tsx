import { useQuery } from "@tanstack/react-query";
import { getStatement, getBalance } from "@/lib/api";
import { formatAmount, formatDate, shortId } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface Props {
  accountId: string;
  accountName: string;
}

/**
 * AccountStatement — displays all POSTED entries for an account in date
 * order with a running balance. Reversal entries show a link to their
 * original entry (US-3 requirement).
 */
export function AccountStatement({ accountId, accountName }: Props) {
  const { data: statement, isLoading, error } = useQuery({
    queryKey: ["statement", accountId],
    queryFn: () => getStatement(accountId),
  });

  const { data: balance } = useQuery({
    queryKey: ["balance", accountId],
    queryFn: () => getBalance(accountId),
  });

  if (isLoading) return <p className="text-muted-foreground p-4">Loading statement…</p>;
  if (error) return <p className="text-destructive p-4">Failed to load statement.</p>;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{accountName} — Statement</CardTitle>
        {balance && (
          <span className="text-sm font-medium text-muted-foreground">
            Balance: <span className="text-foreground font-semibold">{formatAmount(balance.balance)}</span>
          </span>
        )}
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Entry</TableHead>
              <TableHead className="text-right">Debit</TableHead>
              <TableHead className="text-right">Credit</TableHead>
              <TableHead className="text-right">Balance</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {statement?.lines.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No entries yet.
                </TableCell>
              </TableRow>
            )}
            {statement?.lines.map((line) => (
              <TableRow key={line.entry_id}>
                <TableCell className="text-muted-foreground text-xs">
                  {formatDate(line.posted_at)}
                </TableCell>
                <TableCell>
                  <span className="font-mono text-xs">{shortId(line.entry_id)}</span>
                  {/* Reversal link — shown when this entry reverses another (US-3 AC3) */}
                  {line.reversal_of_id && (
                    <Badge variant="secondary" className="ml-2 text-xs">
                      Reversal of #{shortId(line.reversal_of_id)}
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {Number(line.debit) > 0 ? formatAmount(line.debit) : "—"}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {Number(line.credit) > 0 ? formatAmount(line.credit) : "—"}
                </TableCell>
                <TableCell className="text-right font-mono text-sm font-semibold">
                  {formatAmount(line.running_balance)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
