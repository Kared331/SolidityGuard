import { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Table, Tabs, Button, Space, Tag, Typography, Popconfirm, message } from 'antd';
import { ReloadOutlined, FileTextOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import client from '../api/client';

const { Title } = Typography;

interface FileItem {
  id: number;
  file_path: string;
  status: string;
}

interface Analysis {
  id: number;
  detection_ref: string;
  check_name: string;
  description: string;
  impact: string;
  confidence: string;
}

interface FuzzResult {
  id: number;
  created_at: string;
  failures_count: number;
  raw_output: string;
}

interface LLMAuditResult {
  id: number;
  contract_name: string;
  function_name: string;
  vulnerability_description: string;
  severity: string;
  suggested_fix: string;
  gas_optimization: string;
  created_at: string;
}

const severityColors: Record<string, string> = {
  critical: 'red',
  high: 'orange',
  medium: 'gold',
  low: 'blue',
  informational: 'green',
  unknown: 'default',
};

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [files, setFiles] = useState<FileItem[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [fuzzResults, setFuzzResults] = useState<FuzzResult[]>([]);
  const [llmAuditResults, setLlmAuditResults] = useState<LLMAuditResult[]>([]);
  const [loadingFiles, setLoadingFiles] = useState(false);
  const [triggering, setTriggering] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchFiles = useCallback(async () => {
    if (!id) return;
    setLoadingFiles(true);
    try {
      const response = await client.get(`/v1/projects/${id}/files`);
      setFiles(response.data);
    } catch {
      message.error('Failed to load files');
    } finally {
      setLoadingFiles(false);
    }
  }, [id]);

  const fetchAllResults = useCallback(async () => {
    if (!id) return;
    try {
      const [analysesRes, fuzzRes, llmRes] = await Promise.all([
        client.get(`/v1/projects/${id}/analyses`),
        client.get(`/v1/projects/${id}/fuzz-results`),
        client.get(`/v1/projects/${id}/llm-audit-results`),
      ]);
      setAnalyses(analysesRes.data);
      setFuzzResults(fuzzRes.data);
      setLlmAuditResults(llmRes.data);
    } catch {
      // silently fail during polling
    }
  }, [id]);

  useEffect(() => {
    fetchFiles();
    fetchAllResults();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchFiles, fetchAllResults]);

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts++;
      await fetchAllResults();
      if (attempts >= 20) {
        if (pollRef.current) clearInterval(pollRef.current);
        setTriggering(null);
      }
    }, 3000);
  };

  const handleTrigger = async (action: string, endpoint: string) => {
    if (!id) return;
    setTriggering(action);
    try {
      await client.post(`/v1/projects/${id}/${endpoint}`);
      message.success(`${action} started`);
      startPolling();
    } catch {
      message.error(`Failed to start ${action}`);
      setTriggering(null);
    }
  };

  const handleMarkFalsePositive = async (detectionId: number) => {
    try {
      await client.post(`/v1/detections/${detectionId}/mark-false-positive`, {});
      message.success('Marked as false positive');
      fetchAllResults();
    } catch {
      message.error('Failed to mark as false positive');
    }
  };

  const fileColumns = [
    { title: 'File Path', dataIndex: 'file_path', key: 'file_path' },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'ready' ? 'green' : 'default'}>{status}</Tag>
      ),
    },
  ];

  const analysisColumns = [
    { title: 'Check Name', dataIndex: 'check_name', key: 'check_name' },
    { title: 'Description', dataIndex: 'description', key: 'description', ellipsis: true },
    {
      title: 'Impact',
      dataIndex: 'impact',
      key: 'impact',
      render: (impact: string) => (
        <Tag color={severityColors[impact?.toLowerCase()] || 'default'}>{impact}</Tag>
      ),
    },
    { title: 'Confidence', dataIndex: 'confidence', key: 'confidence' },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="Mark as false positive?"
          onConfirm={() => handleMarkFalsePositive(record.id)}
          okText="Yes"
          cancelText="No"
        >
          <Button size="small" danger>Mark FP</Button>
        </Popconfirm>
      ),
    },
  ];

  const fuzzColumns = [
    {
      title: 'Created At',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => new Date(v).toLocaleString(),
    },
    { title: 'Failures', dataIndex: 'failures_count', key: 'failures_count' },
    {
      title: 'Raw Output',
      dataIndex: 'raw_output',
      key: 'raw_output',
      ellipsis: true,
      render: (text: string) => <span title={text}>{text?.substring(0, 100)}...</span>,
    },
  ];

  const llmColumns = [
    { title: 'Contract', dataIndex: 'contract_name', key: 'contract_name' },
    { title: 'Function', dataIndex: 'function_name', key: 'function_name' },
    {
      title: 'Vulnerability',
      dataIndex: 'vulnerability_description',
      key: 'vulnerability_description',
      ellipsis: true,
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={severityColors[severity?.toLowerCase()] || 'default'}>{severity}</Tag>
      ),
    },
    { title: 'Fix', dataIndex: 'suggested_fix', key: 'suggested_fix', ellipsis: true },
  ];

  const tabItems = [
    {
      key: 'slither',
      label: `Slither (${analyses.length})`,
      children: (
        <Table
          dataSource={analyses}
          columns={analysisColumns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No analysis results yet. Run Slither to start.' }}
        />
      ),
    },
    {
      key: 'fuzzing',
      label: `Fuzzing (${fuzzResults.length})`,
      children: (
        <Table
          dataSource={fuzzResults}
          columns={fuzzColumns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No fuzz results yet. Run Fuzzing to start.' }}
        />
      ),
    },
    {
      key: 'llm-audit',
      label: `LLM Audit (${llmAuditResults.length})`,
      children: (
        <Table
          dataSource={llmAuditResults}
          columns={llmColumns}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: 'No LLM audit results yet. Run LLM Audit to start.' }}
        />
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Project #{id}</Title>

      <Card title="Uploaded Files" style={{ marginBottom: 24 }}>
        <Table
          dataSource={files}
          columns={fileColumns}
          rowKey="id"
          loading={loadingFiles}
          pagination={false}
          size="small"
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={fetchFiles}
          style={{ marginTop: 12 }}
          size="small"
        >
          Refresh
        </Button>
      </Card>

      <Card title="Analysis Actions" style={{ marginBottom: 24 }}>
        <Space>
          <Button
            type="primary"
            loading={triggering === 'Slither'}
            onClick={() => handleTrigger('Slither', 'analyze')}
          >
            Run Slither
          </Button>
          <Button
            type="primary"
            loading={triggering === 'Fuzzing'}
            onClick={() => handleTrigger('Fuzzing', 'fuzz')}
          >
            Run Fuzzing
          </Button>
          <Button
            type="primary"
            loading={triggering === 'LLM Audit'}
            onClick={() => handleTrigger('LLM Audit', 'llm-audit')}
          >
            Run LLM Audit
          </Button>
          <Button
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/projects/${id}/report`)}
          >
            Generate Report
          </Button>
        </Space>
      </Card>

      <Card title="Results">
        <Tabs items={tabItems} />
      </Card>
    </div>
  );
}
