import {
	IExecuteFunctions,
	INodeExecutionData,
	INodeType,
	INodeTypeDescription,
	NodeOperationError,
} from 'n8n-workflow';

export class SentinelTriage implements INodeType {
	description: INodeTypeDescription = {
		displayName: 'Sentinel Triage',
		name: 'sentinelTriage',
		icon: 'file:icon.svg',
		group: ['transform'],
		version: 1,
		subtitle: '={{$parameter["alertSource"]}}',
		description: 'Send alerts to Sentinel for AI-powered triage',
		defaults: {
			name: 'Sentinel Triage',
			color: '#3b82f6',
		},
		inputs: ['main'],
		outputs: ['main'],
		credentials: [
			{
				name: 'sentinelApi',
				required: true,
			},
		],
		properties: [
			{
				displayName: 'Alert Source',
				name: 'alertSource',
				type: 'string',
				default: 'webhook',
				required: true,
				description: 'Name of the alert source (e.g., datadog, sentry, custom)',
			},
			{
				displayName: 'Severity',
				name: 'severity',
				type: 'options',
				options: [
					{
						name: 'Critical',
						value: 'critical',
					},
					{
						name: 'High',
						value: 'high',
					},
					{
						name: 'Medium',
						value: 'medium',
					},
					{
						name: 'Low',
						value: 'low',
					},
				],
				default: 'high',
				required: true,
			},
			{
				displayName: 'Message',
				name: 'message',
				type: 'string',
				default: '',
				required: true,
				typeOptions: {
					rows: 3,
				},
				description: 'Alert message or description',
			},
			{
				displayName: 'Metadata (JSON)',
				name: 'metadata',
				type: 'string',
				default: '{}',
				typeOptions: {
					rows: 5,
				},
				description: 'Additional alert metadata as JSON object',
			},
		],
	};

	async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
		const items = this.getInputData();
		const returnData: INodeExecutionData[] = [];

		// Get credentials
		const credentials = await this.getCredentials('sentinelApi');
		if (!credentials) {
			throw new NodeOperationError(this.getNode(), 'No Sentinel API credentials found');
		}

		const backendUrl = (credentials.backendUrl as string) || 'http://localhost:8000';

		for (let i = 0; i < items.length; i++) {
			try {
				const alertSource = this.getNodeParameter('alertSource', i) as string;
				const severity = this.getNodeParameter('severity', i) as string;
				const message = this.getNodeParameter('message', i) as string;
				const metadataStr = this.getNodeParameter('metadata', i) as string;

				let metadata = {};
				try {
					metadata = JSON.parse(metadataStr);
				} catch (e) {
					// If metadata is invalid JSON, log and continue with empty object
					console.warn('Invalid metadata JSON:', metadataStr);
				}

				// Call Sentinel backend /triage endpoint
				const response = await this.helpers.request({
					method: 'POST',
					url: `${backendUrl}/triage`,
					json: {
						source: alertSource,
						severity: severity,
						message: message,
						metadata: metadata,
					},
					timeout: 30000,
				});

				returnData.push({
					json: response as unknown as Record<string, unknown>,
					pairedItem: {
						item: i,
					},
				});
			} catch (error) {
				if (this.continueOnFail()) {
					returnData.push({
						json: {
							error: error instanceof Error ? error.message : 'Unknown error',
							severity: this.getNodeParameter('severity', i),
						},
						pairedItem: {
							item: i,
						},
					});
				} else {
					throw new NodeOperationError(
						this.getNode(),
						`Failed to triage alert: ${error instanceof Error ? error.message : 'Unknown error'}`,
						{ itemIndex: i },
					);
				}
			}
		}

		return [returnData];
	}
}
