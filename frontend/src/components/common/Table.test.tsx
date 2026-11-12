import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@components/common/Table';

describe('Table UI Component', () => {
  it('renders Table structure correctly', () => {
    render(
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Mã VB</TableHead>
            <TableHead>Trích yếu</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell>VB-001</TableCell>
            <TableCell>Báo cáo tình hình an ninh mạng</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    );

    expect(screen.getByText('Mã VB')).toBeInTheDocument();
    expect(screen.getByText('Trích yếu')).toBeInTheDocument();
    expect(screen.getByText('VB-001')).toBeInTheDocument();
    expect(screen.getByText('Báo cáo tình hình an ninh mạng')).toBeInTheDocument();
  });
});

