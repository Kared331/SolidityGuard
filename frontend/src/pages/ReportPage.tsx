import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Radio, Button, Spin, Typography, Space, List, message } from 'antd';
import { DownloadOutlined, FileTextOutlined } from '@ant-design/icons';
import client from '../api/client';

const { Title, Text } = Typography;

interface ReportItem {
  id: number;
  title: string;
  file_paths: Record<string, string> | null;
  created_at: string;
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [format, setFormat] = useState<'html' | 'pdf' | 'word'>('pdf');
  const [generating, setGenerating] = useState(false);
  const [reports, setReports] = useState<ReportItem[]>([]);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const initialCountRef = useRef(0);

  const fetchReports = useCallback(async () => {
    if (!id) return;
    try {
      const response = await client.get(`/v1/projects/${id}/reports`);
      setReports(response.data);
      return response.data.length as number;
    } catch {
      return -1;
    }
  }, [id]);

  useEffect(() => {
    fetchReports();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchReports]);

  const handleGenerate = async () => {
    if (!id) return;
    setGenerating(true);
    initialCountRef.current = reports.length;

    try {
      await client.post(`/v1/projects/${id}/report`, { format });
      message.success('Report generation started');

      // Stop any existing polling
      if (pollRef.current) clearInterval(pollRef.current);

      // Poll for new reports
      let attempts = 0;
      pollRef.current = setInterval(async () => {
        attempts++;
        const count = await fetchReports();

        // Stop if new report appeared or timeout
        if (count > initialCountRef.current || attempts >= 20) {
          if (pollRef.current) clearInterval(pollRef.current);
          setGenerating(false);
          if (count > initialCountRef.current) {
            message.success('Report generated successfully');
          } else {
            message.warning('Report generation is taking longer than expected. Please refresh.');
          }
        }
      }, 3000);
    } catch {
      message.error('Failed to start report generation');
      setGenerating(false);
    }
  };

  const handleDownload = (reportId: number, fmt: string) => {
    const downloadUrl = `/api/v1/reports/${reportId}/download?format=${fmt}`;
    window.open(downloadUrl, '_blank');
  };

  return (
    <Card style={{ maxWidth: 700, margin: '60px auto' }}>
      <Title level={2}>Generate Report</Title>
      <Text type="secondary">Project #{id}</Text>

      <Space direction="vertical" size="large" style={{ width: '100%', marginTop: 24 }}>
        <div>
          <Text strong>Select format:</Text>
          <br />
          <Radio.Group
            value={format}
            onChange={(e) => setFormat(e.target.value)}
            optionType="button"
            buttonStyle="solid"
            style={{ marginTop: 8 }}
          >
            <Radio.Button value="html">HTML</Radio.Button>
            <Radio.Button value="pdf">PDF</Radio.Button>
            <Radio.Button value="word">Word</Radio.Button>
          </Radio.Group>
        </div>

        <Spin spinning={generating}>
          <Button
            type="primary"
            icon={<FileTextOutlined />}
            onClick={handleGenerate}
            disabled={generating}
            size="large"
          >
            {generating ? 'Generating...' : 'Generate Report'}
          </Button>
        </Spin>

        {reports.length > 0 && (
          <Card title="Available Reports" size="small">
            <List
              dataSource={reports}
              renderItem={(report) => (
                <List.Item
                  actions={[
                    report.file_paths?.html && (
                      <Button
                        key="html"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => handleDownload(report.id, 'html')}
                      >
                        HTML
                      </Button>
                    ),
                    report.file_paths?.pdf && (
                      <Button
                        key="pdf"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => handleDownload(report.id, 'pdf')}
                      >
                        PDF
                      </Button>
                    ),
                    report.file_paths?.word && (
                      <Button
                        key="word"
                        size="small"
                        icon={<DownloadOutlined />}
                        onClick={() => handleDownload(report.id, 'word')}
                      >
                        Word
                      </Button>
                    ),
                  ].filter(Boolean)}
                >
                  <List.Item.Meta
                    title={report.title}
                    description={new Date(report.created_at).toLocaleString()}
                  />
                </List.Item>
              )}
            />
          </Card>
        )}
      </Space>
    </Card>
  );
}
