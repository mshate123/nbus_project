import { useQuery } from "@tanstack/react-query";
import { getRateSchedule } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

/**
 * RateSchedule — displays the current interest rate schedule by tier (US-6).
 * Annual rate shown as both decimal and percentage.
 */
export function RateSchedule() {
  const { data: rates, isLoading, error } = useQuery({
    queryKey: ["rate-schedule"],
    queryFn: getRateSchedule,
  });

  if (isLoading) return <p className="text-muted-foreground p-4">Loading rate schedule…</p>;
  if (error) return <p className="text-destructive p-4">Failed to load rate schedule.</p>;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Interest Rate Schedule</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tier</TableHead>
              <TableHead className="text-right">Annual Rate (APY)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rates?.map((entry) => (
              <TableRow key={entry.tier}>
                <TableCell className="capitalize">{entry.tier}</TableCell>
                <TableCell className="text-right font-mono">
                  {(Number(entry.annual_rate) * 100).toFixed(2)}%
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
