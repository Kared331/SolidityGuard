import { useState, useEffect, useCallback } from 'react';
import { Card, Input, Table, Tag, Typography, Descriptions } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import client from '../api/client';

const { Title } = Typography;

interface VulnerabilityItem {
  id: number;
  swc_id: string;
  title: string;
  description: string;
  severity: string | null;
  code_example: string | null;
}

interface VulnerabilityResponse {
  total: number;
  page: number;
  page_size: number;
  items: VulnerabilityItem[];
}

const severityColors: Record<string, string> = {
  critical: 'red',
  high: 'orange',
  medium: 'gold',
  low: 'blue',
  informational: 'green',
};

export default function VulnerabilitiesPage() {
  const [vulnerabilities, setVulnerabilities] = useState<VulnerabilityItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);

  const fetchVulnerabilities = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number> = {
        page,
        page_size: pageSize,
      };
      if (search) params.search = search;
      const res = await client.get<VulnerabilityResponse>('/v1/vulnerabilities', { params });
      setVulnerabilities(res.data.items);
      setTotal(res.data.total);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search]);

  useEffect(() => {
    fetchVulnerabilities();
  }, [fetchVulnerabilities]);

  const columns: ColumnsType<VulnerabilityItem> = [
    { title: 'SWC ID', dataIndex: 'swc_id', key: 'swc_id', width: 120 },
    { title: 'Title', dataIndex: 'title', key: 'title', width: 200 },
    { title: 'Description', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      width: 120,
      render: (severity: string | null) =>
        severity ? (
          <Tag color={severityColors[severity.toLowerCase()] || 'default'}>{severity}</Tag>
        ) : (
          <Tag>N/A</Tag>
        ),
    },
  ];

  return (
    <div>
      <Title level={2}>Vulnerability Database</Title>
      <Card>
        <Input.Search
          placeholder="Search vulnerabilities..."
          onSearch={(value) => {
            setSearch(value);
            setPage(1);
          }}
          enterButton
          style={{ marginBottom: 16, maxWidth: 400 }}
        />
        <Table
          dataSource={vulnerabilities}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            onChange: (p, ps) => {
              setPage(p);
              setPageSize(ps);
            },
          }}
          expandable={{
            expandedRowRender: (record) => (
              <div style={{ padding: 16 }}>
                <Descriptions bordered column={1} size="small">
                  <Descriptions.Item label="Description">
                    {record.description}
                  </Descriptions.Item>
                </Descriptions>
                {record.code_example && (
                  <div style={{ marginTop: 12 }}>
                    <strong>Code Example:</strong>
                    <pre
                      style={{
                        background: '#f5f5f5',
                        padding: 12,
                        borderRadius: 4,
                        marginTop: 8,
                        overflow: 'auto',
                      }}
                    >
                      <code>{record.code_example}</code>
                    </pre>
                  </div>
                )}
              </div>
            ),
            rowExpandable: () => true,
          }}
        />
      </Card>
    </div>
  );
}
